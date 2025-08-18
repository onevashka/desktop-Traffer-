import traceback
import threading
import asyncio
import queue
import time
from typing import Optional
from datetime import datetime
from loguru import logger
from pathlib import Path
from dataclasses import dataclass

from src.entities.moduls.inviter import InviteUser, UserStatus
from .utils import check_chat_limits, check_account_limits, ensure_username_for_account
from src.entities.moduls.inviter import *

# Импорты Telethon
from telethon.tl.functions.users import GetFullUserRequest
from telethon.tl.functions.messages import GetCommonChatsRequest
from telethon.errors import (
    UsernameInvalidError, UsernameNotOccupiedError, PeerFloodError, FloodWaitError,
    UserPrivacyRestrictedError, UserDeactivatedBanError, UserDeactivatedError,
    AuthKeyUnregisteredError, SessionRevokedError
)
from telethon.tl.types import ChatAdminRights
from telethon.tl.functions.channels import EditAdminRequest


class ChatWorkerThread(threading.Thread):
    """Поток для одного чата - управляет потоками с автоматической сменой аккаунтов"""

    def __init__(self, chat_id: int, chat_link: str, parent):
        super().__init__(name=f"Chat-{chat_id}")
        self.chat_id = chat_id
        self.chat_link = chat_link
        self.parent = parent
        self.chat_success = 0
        self.chat_total = 0
        self.chat_accounts_used = set()  # НОВОЕ!
        self.active_threads = []
        self.threads_lock = threading.Lock()
        self.stop_chat_flag = threading.Event()

        # Инициализируем статистику чата
        if chat_link not in parent.chat_stats:
            parent.chat_stats[chat_link] = {"success": 0, "total": 0}

    def run(self):
        """🔥 ОБНОВЛЕНО: Основной цикл чата с ОБЯЗАТЕЛЬНЫМ отзывом прав при любом завершении"""
        # Проверяем готовность чата
        if self.chat_link not in self.parent.ready_chats:
            logger.error(f"[{self.parent.profile_name}]-[Поток-{self.chat_id}]-[{self.chat_link}] Чат не готов")
            return

        module_name = f"admin_inviter_{self.parent.profile_name}"
        chat_finish_reason = "неизвестная причина"

        try:
            # ================================================================
            # ОСНОВНОЙ ЦИКЛ РАБОТЫ ЧАТА
            # ================================================================
            while not self.parent.stop_flag.is_set() and not self.stop_chat_flag.is_set():

                # 🚫 ПРОВЕРКА: Чат заблокирован системой защиты
                if self.parent.chat_protection_manager.is_chat_blocked(self.chat_link):
                    chat_finish_reason = "чат заблокирован системой защиты"
                    logger.error(
                        f"[{self.parent.profile_name}]-[Поток-{self.chat_id}]-[{self.chat_link}] "
                        f"❌ ЧАТ ЗАБЛОКИРОВАН системой защиты - завершаем работу"
                    )
                    break

                # 🎯 ПРОВЕРКА: Достигнут лимит чата
                if not check_chat_limits(self.parent, self.chat_success):
                    chat_finish_reason = "достигнут лимит чата"
                    logger.success(
                        f"[{self.parent.profile_name}]-[Поток-{self.chat_id}]-[{self.chat_link}] Достигнут лимит чата")
                    break

                # 👥 ПРОВЕРКА: Закончились пользователи
                if self.parent.user_queue.empty():
                    chat_finish_reason = "закончились пользователи"
                    logger.info(
                        f"[{self.parent.profile_name}]-[Поток-{self.chat_id}]-[{self.chat_link}] Нет пользователей")
                    break

                # 🔄 УПРАВЛЕНИЕ WORKER ПОТОКАМИ
                with self.threads_lock:
                    self.active_threads = [t for t in self.active_threads if t.is_alive()]
                    active_count = len(self.active_threads)

                needed = self.parent.config.threads_per_chat - active_count
                if needed > 0:
                    # 💰 ПРОВЕРКА: Есть ли аккаунты
                    if not self.parent.check_accounts_availability():
                        if active_count == 0:
                            chat_finish_reason = "закончились аккаунты и нет активных потоков"
                            logger.info(
                                f"[{self.parent.profile_name}]-[Поток-{self.chat_id}]-[{self.chat_link}] Нет аккаунтов и потоков - завершаем")
                            break
                        time.sleep(10)
                        continue

                    # 🚀 ЗАПУСК новых worker потоков
                    for i in range(needed):
                        worker = WorkerThread(
                            thread_id=active_count + i + 1,
                            chat_thread=self,
                            module_name=module_name
                        )
                        worker.start()

                        with self.threads_lock:
                            self.active_threads.append(worker)

                        logger.success(
                            f"[{self.parent.profile_name}]-[Поток-{self.chat_id}]-[{self.chat_link}] Запущен поток-{active_count + i + 1}")

                time.sleep(5)

            # ================================================================
            # НОРМАЛЬНОЕ ЗАВЕРШЕНИЕ ЧАТА
            # ================================================================

            logger.info(
                f"[{self.parent.profile_name}]-[Поток-{self.chat_id}]-[{self.chat_link}] "
                f"🛑 Завершение работы чата. Причина: {chat_finish_reason}")

            # 1️⃣ ЖДЕМ ЗАВЕРШЕНИЯ ВСЕХ WORKER ПОТОКОВ
            self._wait_for_worker_threads()

            # 2️⃣ ОТЗЫВАЕМ ПРАВА У ГЛАВНОГО АДМИНА
            self._revoke_main_admin_rights_sync(chat_finish_reason)

        except Exception as e:
            # ================================================================
            # АВАРИЙНОЕ ЗАВЕРШЕНИЕ ЧАТА ПРИ ОШИБКЕ
            # ================================================================
            chat_finish_reason = f"критическая ошибка: {str(e)[:100]}"
            logger.error(
                f"[{self.parent.profile_name}]-[Поток-{self.chat_id}]-[{self.chat_link}] 💥 Критическая ошибка: {e}")

            # 1️⃣ ЖДЕМ ЗАВЕРШЕНИЯ WORKER ПОТОКОВ (быстро)
            self._wait_for_worker_threads(timeout=30)

            # 2️⃣ ОТЗЫВАЕМ ПРАВА У ГЛАВНОГО АДМИНА (даже при ошибке!)
            try:
                self._revoke_main_admin_rights_sync(chat_finish_reason)
            except Exception as cleanup_error:
                logger.error(
                    f"[{self.parent.profile_name}]-[Поток-{self.chat_id}]-[{self.chat_link}] "
                    f"❌ Ошибка отзыва прав при аварийном завершении: {cleanup_error}")

        finally:
            # ================================================================
            # ФИНАЛЬНАЯ ЗАЩИТА - ПОСЛЕДНЯЯ ПОПЫТКА ОТЗЫВА ПРАВ
            # ================================================================
            try:
                logger.debug(
                    f"[{self.parent.profile_name}]-[Поток-{self.chat_id}]-[{self.chat_link}] "
                    f"🔒 ФИНАЛЬНАЯ проверка отзыва прав главного админа...")

                self._revoke_main_admin_rights_sync("финальная защита")

            except Exception as final_error:
                logger.error(
                    f"[{self.parent.profile_name}]-[Поток-{self.chat_id}]-[{self.chat_link}] "
                    f"❌ Ошибка финальной защиты отзыва прав: {final_error}")

            logger.debug(
                f"[{self.parent.profile_name}]-[Поток-{self.chat_id}]-[{self.chat_link}] "
                f"🏁 ChatWorkerThread полностью завершен")

    def _wait_for_worker_threads(self, timeout: int = 60):
        """🔄 Ожидание завершения всех worker потоков"""
        logger.debug(
            f"[{self.parent.profile_name}]-[Поток-{self.chat_id}]-[{self.chat_link}] "
            f"⏳ Ожидаем завершения всех worker потоков...")

        with self.threads_lock:
            threads_to_wait = self.active_threads.copy()

        if threads_to_wait:
            logger.info(
                f"[{self.parent.profile_name}]-[Поток-{self.chat_id}]-[{self.chat_link}] "
                f"⏳ Найдено {len(threads_to_wait)} активных потоков")

            for i, worker in enumerate(threads_to_wait, 1):
                if worker.is_alive():
                    logger.info(
                        f"[{self.parent.profile_name}]-[Поток-{self.chat_id}]-[{self.chat_link}] "
                        f"⏳ Ожидаем worker поток {i}/{len(threads_to_wait)}")

                    worker.join(timeout=600)

                    if worker.is_alive():
                        logger.warning(
                            f"[{self.parent.profile_name}]-[Поток-{self.chat_id}]-[{self.chat_link}] "
                            f"⚠️ Worker поток {i} не завершился за {timeout} секунд")
                    else:
                        logger.success(
                            f"[{self.parent.profile_name}]-[Поток-{self.chat_id}]-[{self.chat_link}] "
                            f"✅ Worker поток {i} успешно завершен")

            logger.success(
                f"[{self.parent.profile_name}]-[Поток-{self.chat_id}]-[{self.chat_link}] "
                f"✅ Все worker потоки обработаны")
        else:
            logger.info(
                f"[{self.parent.profile_name}]-[Поток-{self.chat_id}]-[{self.chat_link}] "
                f"ℹ️ Нет активных потоков для ожидания")

    # ПОЛНОСТЬЮ ЗАМЕНИТЕ метод _revoke_main_admin_rights_sync в ChatWorkerThread:

    def _revoke_main_admin_rights_sync(self, reason: str):
        """👑🔒 ИСПРАВЛЕННАЯ СИНХРОННАЯ ОБЕРТКА - теперь использует систему команд бота"""
        try:
            logger.debug(
                f"[{self.parent.profile_name}]-[Поток-{self.chat_id}]-[{self.chat_link}] "
                f"👑🔒 Отзываем права у главного админа... (причина: {reason})")

            # 🔥 НОВОЕ: Проверяем наличие админа
            if self.chat_link not in self.parent.chat_admins:
                logger.warning(
                    f"[{self.parent.profile_name}]-[Поток-{self.chat_id}]-[{self.chat_link}] "
                    f"⚠️ Главный админ для чата не найден")
                return

            admin_data = self.parent.chat_admins[self.chat_link]

            # Проверяем наличие данных
            if not hasattr(admin_data, 'user_id') or not hasattr(admin_data, 'chat_id'):
                logger.warning(
                    f"[{self.parent.profile_name}]-[Поток-{self.chat_id}]-[{self.chat_link}] "
                    f"⚠️ Данные админа {admin_data.name} не сохранены")
                return

            if not admin_data.user_id or not admin_data.chat_id:
                logger.warning(
                    f"[{self.parent.profile_name}]-[Поток-{self.chat_id}]-[{self.chat_link}] "
                    f"⚠️ ID или chat_id админа {admin_data.name} пустые")
                return

            # 🔥 НОВОЕ: Используем систему команд бота из основного потока!
            try:
                success = self.parent.send_bot_command(
                    action="REVOKE_ADMIN_RIGHTS",
                    chat_id=admin_data.chat_id,
                    user_id=admin_data.user_id,
                    account_name=admin_data.name,
                    timeout=15  # 15 секунд таймаут
                )

                if success:
                    logger.info(
                        f"[{self.parent.profile_name}]-[Поток-{self.chat_id}]-[{self.chat_link}] "
                        f"✅ Права у главного админа {admin_data.name} успешно отозваны через систему команд")
                else:
                    logger.warning(
                        f"[{self.parent.profile_name}]-[Поток-{self.chat_id}]-[{self.chat_link}] "
                        f"⚠️ Не удалось отозвать права у главного админа {admin_data.name}")

            except Exception as command_error:
                logger.error(
                    f"[{self.parent.profile_name}]-[Поток-{self.chat_id}]-[{self.chat_link}] "
                    f"❌ Ошибка отправки команды боту: {command_error}")

        except Exception as e:
            logger.warning(
                f"[{self.parent.profile_name}]-[Поток-{self.chat_id}]-[{self.chat_link}] "
                f"❌ Ошибка отзыва прав у главного админа (игнорируем): {e}")


class WorkerThread(threading.Thread):
    """
    🔥 ОБНОВЛЕННЫЙ поток с системой реального времени и персональными очередями админов
    """

    def __init__(self, thread_id: int, chat_thread: ChatWorkerThread, module_name: str):
        super().__init__(name=f"Thread-{thread_id}")
        self.thread_id = thread_id
        self.chat_thread = chat_thread
        self.module_name = module_name
        self.current_account_data = None
        self.current_account_name = "НетАккаунта"
        self.thread_account = None
        self.realtime_logger = None  # ДОБАВЛЕНО: Будет установлен родителем

    def run(self):
        """Основной метод потока - теперь управляет несколькими аккаунтами"""
        try:
            # Проверяем готовность чата
            if self.chat_thread.chat_link not in self.chat_thread.parent.ready_chats:
                logger.error(
                    f"[{self.chat_thread.parent.profile_name}]-[Поток-{self.chat_thread.chat_id}]-[{self.chat_thread.chat_link}]-[Поток-{self.thread_id}] Чат не готов")
                return

            # Создаем event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # Запускаем логику с автоматической сменой аккаунтов
            loop.run_until_complete(self._thread_logic())

        except Exception as e:
            logger.error(
                f"[{self.chat_thread.parent.profile_name}]-[Поток-{self.chat_thread.chat_id}]-[{self.chat_thread.chat_link}]-[Поток-{self.thread_id}] Ошибка: {e}")
        finally:
            # ДОБАВЛЕНО: Логирование завершения потока
            logger.info(
                f"[{self.chat_thread.parent.profile_name}]-[Поток-{self.chat_thread.chat_id}]-[{self.chat_thread.chat_link}]-[Поток-{self.thread_id}] ✅ Worker поток завершен")
            if 'loop' in locals():
                loop.close()

    async def _thread_logic(self):
        """Основная логика потока с автоматической сменой аккаунтов"""
        chat_id = self.chat_thread.chat_id

        # ОСНОВНОЙ ЦИКЛ ПОТОКА - продолжает работать пока есть пользователи и аккаунты
        while not self.chat_thread.parent.stop_flag.is_set():

            if self.chat_thread.stop_chat_flag.is_set():
                logger.debug(
                    f"[{self.chat_thread.parent.profile_name}]-[Поток-{chat_id}]-"
                    f"[{self.chat_thread.chat_link}]-[Поток-{self.thread_id}] "
                    f"🛑 ФЛАГ ОСТАНОВКИ ЧАТА УСТАНОВЛЕН - ЗАВЕРШАЕМ ПОТОК"
                )
                break

                # 🔥 ПРОВЕРКА БЛОКИРОВКИ ЧАТА ЧЕРЕЗ МЕНЕДЖЕР
            if self.chat_thread.parent.chat_protection_manager.is_chat_blocked(self.chat_thread.chat_link):
                logger.error(
                    f"[{self.chat_thread.parent.profile_name}]-[Поток-{chat_id}]-"
                    f"[{self.chat_thread.chat_link}]-[Поток-{self.thread_id}] "
                    f"❌ ЧАТ ЗАБЛОКИРОВАН - ЗАВЕРШАЕМ ПОТОК"
                )
                break

            # Проверяем есть ли пользователи для обработки
            if self.chat_thread.parent.user_queue.empty():
                logger.info(
                    f"[{self.chat_thread.parent.profile_name}]-[Поток-{chat_id}]-[{self.chat_thread.chat_link}]-[Поток-{self.thread_id}] Нет пользователей - завершаем поток")
                break

            # Проверяем лимиты чата
            if not check_chat_limits(self.chat_thread.parent, self.chat_thread.chat_success):
                break

            # ПОЛУЧАЕМ НОВЫЙ АККАУНТ для работы
            fresh_accounts = self.chat_thread.parent.get_fresh_accounts(self.module_name, 1)

            if not fresh_accounts:
                logger.warning(
                    f"[{self.chat_thread.parent.profile_name}]-[Поток-{chat_id}]-[{self.chat_thread.chat_link}]-[Поток-{self.thread_id}] Нет доступных аккаунтов - завершаем поток")
                break

            # Обновляем данные аккаунта
            self.current_account_data = fresh_accounts[0]
            self.current_account_name = self.current_account_data.name
            self.thread_account = None

            logger.info(
                f"[{self.chat_thread.parent.profile_name}]-[Поток-{chat_id}]-[{self.chat_thread.chat_link}]-[Поток-{self.thread_id}] 🔄 Начинаем работу с аккаунтом: {self.current_account_name}")

            # РАБОТАЕМ С ТЕКУЩИМ АККАУНТОМ до его завершения
            account_finished = await self._work_with_current_account()

            if account_finished:
                logger.info(
                    f"[{self.chat_thread.parent.profile_name}]-[Поток-{chat_id}]-[{self.chat_thread.chat_link}]-[Поток-{self.thread_id}] ✅ Аккаунт {self.current_account_name} завершен, переходим к следующему")
                # Продолжаем цикл для получения нового аккаунта
                continue
            else:
                # Если аккаунт завершился по критической ошибке - завершаем поток
                logger.error(
                    f"[{self.chat_thread.parent.profile_name}]-[Поток-{chat_id}]-[{self.chat_thread.chat_link}]-[Поток-{self.thread_id}] ❌ Критическая ошибка - завершаем поток")
                break

    def _block_chat_immediately(self, reason: str):
        """🔥 НОВЫЙ МЕТОД: Немедленная блокировка чата без счетчиков"""
        try:
            chat_link = self.chat_thread.chat_link

            # Добавляем чат в заблокированные
            self.chat_thread.parent.chat_protection_manager.blocked_chats.add(chat_link)

            # Записываем в файл остановленных чатов
            self.chat_thread.parent.record_stopped_chat(chat_link, reason)

            # Останавливаем все потоки этого чата
            self.chat_thread.stop_chat_flag.set()

            logger.error(f"🚫 [{self.chat_thread.parent.profile_name}] ЧАТ НЕМЕДЛЕННО ЗАБЛОКИРОВАН: {chat_link}")
            logger.error(f"🚫 [{self.chat_thread.parent.profile_name}] Причина: {reason}")

        except Exception as e:
            logger.error(f"[{self.chat_thread.parent.profile_name}] ❌ Ошибка блокировки чата: {e}")

    async def _work_with_current_account(self) -> bool:
        """
        🔥 ОБНОВЛЕНО: Работает с текущим аккаунтом до его завершения - теперь использует персональные очереди

        Returns:
            True - если аккаунт успешно завершен (достиг лимита/проблемы), можно брать следующий
            False - если критическая ошибка, нужно завершить поток
        """
        chat_id = self.chat_thread.chat_id
        client_connected = False
        rights_granted = False
        account_finish_reason = "unknown"

        # КРИТИЧНО: Регистрируем аккаунт для ЭТОГО чата
        self.chat_thread.chat_accounts_used.add(self.current_account_name)

        # 🔥 ПРОВЕРКА ФЛАГА ОСТАНОВКИ ЧАТА В НАЧАЛЕ!
        if self.chat_thread.stop_chat_flag.is_set():
            logger.error(
                f"[{self.chat_thread.parent.profile_name}]-[Поток-{chat_id}]-"
                f"[{self.chat_thread.chat_link}]-[{self.current_account_name}] "
                f"🛑 ФЛАГ ОСТАНОВКИ ЧАТА УСТАНОВЛЕН - НЕ НАЧИНАЕМ РАБОТУ"
            )
            return True

        # 🔥 ПРОВЕРКА БЛОКИРОВКИ ЧАТА В НАЧАЛЕ!
        if self.chat_thread.parent.chat_protection_manager.is_chat_blocked(self.chat_thread.chat_link):
            logger.error(
                f"[{self.chat_thread.parent.profile_name}]-[Поток-{chat_id}]-"
                f"[{self.chat_thread.chat_link}]-[{self.current_account_name}] "
                f"❌ ЧАТ ЗАБЛОКИРОВАН - НЕ НАЧИНАЕМ РАБОТУ"
            )
            return True

        try:
            # 1. Проверяем файлы аккаунта
            session_path = self.current_account_data.account.session_path
            json_path = self.current_account_data.account.json_path

            if not Path(session_path).exists():
                logger.error(
                    f"[{self.chat_thread.parent.profile_name}]-[Поток-{chat_id}]-[{self.chat_thread.chat_link}]-[{self.current_account_name}] Файл сессии не найден: {session_path}")
                await self._ensure_disconnected()
                await self._handle_problem("missing_files")
                return True

            if not Path(json_path).exists():
                logger.error(
                    f"[{self.chat_thread.parent.profile_name}]-[Поток-{chat_id}]-[{self.chat_thread.chat_link}]-[{self.current_account_name}] JSON файл не найден: {json_path}")
                await self._ensure_disconnected()
                await self._handle_problem("missing_files")
                return True

            # 2. Создание и подключение аккаунта
            from src.accounts.impl.account import Account
            self.thread_account = Account(session_path=session_path, json_path=json_path)
            await self.thread_account.create_client()

            await self.thread_account.connect()

            client_connected = True

            if not await self.thread_account.client.is_user_authorized():
                logger.error(
                    f"[{self.chat_thread.parent.profile_name}]-[Поток-{chat_id}]-[{self.chat_thread.chat_link}]-[{self.current_account_name}] Не авторизован")
                await self._ensure_disconnected()
                await self._handle_problem("dead")
                await self._finalize_current_account(False)
                return True

            me = await self.thread_account.client.get_me()
            logger.info(
                f"[{self.chat_thread.parent.profile_name}]-[Поток-{chat_id}]-[{self.chat_thread.chat_link}]-[{self.current_account_name}] Подключен: {me.first_name}")

            # 3. Вход в чат
            join_result = await self._join_chat()
            if join_result == "FROZEN_ACCOUNT":
                logger.warning(
                    f"[{self.chat_thread.parent.profile_name}]-[Поток-{chat_id}]-[{self.chat_thread.chat_link}]-[{self.current_account_name}] Аккаунт заморожен")

                should_block_chat = self.chat_thread.parent.chat_protection_manager.check_chat_protection(
                    self.chat_thread.chat_link,
                    self.current_account_name,
                    "frozen"  # Тип проблемы - заморозка
                )

                if should_block_chat:
                    logger.debug(
                        f"[{self.chat_thread.parent.profile_name}]-[Поток-{chat_id}]-"
                        f"[{self.chat_thread.chat_link}]-[{self.current_account_name}] "
                        f"🚫 ЧАТ ЗАБЛОКИРОВАН после заморозки аккаунта"
                    )
                    self.chat_thread.stop_chat_flag.set()

                await self._ensure_disconnected()
                await self._handle_problem("frozen")
                await self._finalize_current_account(False)
                return True
            elif join_result != "SUCCESS":
                await self._ensure_disconnected()
                await self._handle_problem("dead")
                return True

            # 4. 🔥 ИСПРАВЛЕНО: Получение прав через персональную очередь чата
            user_entity = await self.thread_account.client.get_entity('me')
            username_thread_account = await ensure_username_for_account(account=self.thread_account,
                                                                        account_name=self.thread_account.name)
            response_queue = queue.Queue()
            command = AdminCommand(
                action="GRANT_RIGHTS",
                worker_name=self.current_account_name,
                worker_user_id=user_entity.id,
                worker_access_hash=user_entity.access_hash,
                chat_link=self.chat_thread.chat_link,
                response_queue=response_queue,
                username=username_thread_account
            )

            # 🔥 КРИТИЧНО: Отправляем команду в персональную очередь ЭТОГО чата!
            admin_name = self.chat_thread.parent.chat_admins[self.chat_thread.chat_link].name

            self.chat_thread.parent.send_command_to_chat(self.chat_thread.chat_link, command)

            try:
                rights_granted = response_queue.get(timeout=250)
            except queue.Empty:
                logger.error(
                    f"[{self.chat_thread.parent.profile_name}]-[Поток-{chat_id}]-[{self.chat_thread.chat_link}]-[{self.current_account_name}] ❌ Таймаут получения прав от админа {admin_name}")
                await self._ensure_disconnected()
                return True

            if rights_granted == "TOO_MANY_ADMINS":
                logger.error(
                    f"[{self.chat_thread.parent.profile_name}]-[Поток-{chat_id}]-[{self.chat_thread.chat_link}]-[{self.current_account_name}] 👑❌ СЛИШКОМ МНОГО АДМИНОВ - БЛОКИРУЕМ ЧАТ НЕМЕДЛЕННО!")

                # 🔥 БЛОКИРУЕМ ЧАТ СРАЗУ БЕЗ СЧЕТЧИКОВ!
                self._block_chat_immediately("Слишком много администраторов в чате")

                await self._ensure_disconnected()
                return True

            if not rights_granted:
                logger.error(
                    f"[{self.chat_thread.parent.profile_name}]-[Поток-{chat_id}]-[{self.chat_thread.chat_link}]-[{self.current_account_name}] ❌ Права не выданы админом {admin_name}")
                await self._ensure_disconnected()
                return True

            logger.info(
                f"[{self.chat_thread.parent.profile_name}]-[Поток-{chat_id}]-[{self.chat_thread.chat_link}]-[{self.current_account_name}] ✅ Права получены от админа {admin_name}")

            # НОВОЕ: Устанавливаем систему реального времени
            self.realtime_logger = self.chat_thread.parent.realtime_logger

            # 5. ГЛАВНЫЙ ЦИКЛ ИНВАЙТИНГА для текущего аккаунта
            invites_count = 0

            while not self.chat_thread.parent.stop_flag.is_set() and not self.chat_thread.stop_chat_flag.is_set():

                if self.chat_thread.parent.chat_protection_manager.is_chat_blocked(self.chat_thread.chat_link):
                    logger.error(
                        f"[{self.chat_thread.parent.profile_name}]-[Поток-{chat_id}]-"
                        f"[{self.chat_thread.chat_link}]-[{self.current_account_name}] "
                        f"❌ ЧАТ ЗАБЛОКИРОВАН - прекращаем работу"
                    )
                    account_finish_reason = "chat_blocked"
                    break

                # Проверки лимитов
                if not check_account_limits(self.chat_thread.parent, self.current_account_name, invites_count):
                    logger.info(
                        f"[{self.chat_thread.parent.profile_name}]-[Поток-{chat_id}]-[{self.chat_thread.chat_link}]-[{self.current_account_name}] Достигнут лимит аккаунта")
                    break

                if not check_chat_limits(self.chat_thread.parent, self.chat_thread.chat_success):
                    logger.info(
                        f"[{self.chat_thread.parent.profile_name}]-[Поток-{chat_id}]-[{self.chat_thread.chat_link}]-[{self.current_account_name}] Достигнут лимит чата")
                    break

                # Получаем пользователя
                try:
                    user = self.chat_thread.parent.user_queue.get_nowait()
                except queue.Empty:
                    logger.info(
                        f"[{self.chat_thread.parent.profile_name}]-[Поток-{chat_id}]-[{self.chat_thread.chat_link}]-[{self.current_account_name}] Нет пользователей")
                    break

                # Инвайтим пользователя
                try:
                    result = await self._invite_user(user)

                    # Счетчики обновляются ВСЕГДА для всех результатов кроме USER_ALREADY
                    if result != "USER_ALREADY":
                        self.chat_thread.chat_total += 1
                        self.chat_thread.parent.chat_stats[self.chat_thread.chat_link]["total"] += 1

                    if result == "SUCCESS":
                        invites_count += 1
                        self.chat_thread.chat_success += 1
                        self.chat_thread.parent.chat_stats[self.chat_thread.chat_link]["success"] += 1

                        logger.success(
                            f"[{self.chat_thread.parent.profile_name}]-[Поток-{chat_id}]-[{self.chat_thread.chat_link}]-[{self.current_account_name}] ✅ УСПЕШНО ДОБАВЛЕН #{invites_count}: @{user.username}")

                        self.chat_thread.parent.chat_protection_manager.check_chat_protection(
                            self.chat_thread.chat_link,
                            self.current_account_name,
                            "success"
                        )

                        # Сбрасываем счетчики ошибок при успехе
                        self.chat_thread.parent._check_account_error_limits(self.current_account_name, "success")
                        self.chat_thread.parent.update_account_stats(self.current_account_name, success=True)

                        # Проверяем достижение лимита успехов
                        if self.current_account_name in self.chat_thread.parent.finished_successfully_accounts:
                            logger.success(
                                f"[{self.chat_thread.parent.profile_name}]-[Поток-{chat_id}]-[{self.chat_thread.chat_link}]-[{self.current_account_name}] 🎯 ДОСТИГ ЛИМИТА УСПЕХОВ - завершаем аккаунт")

                            # Обновляем статус в менеджере
                            await self._update_account_status_in_manager("finished")
                            break

                    elif result == "FLOOD_WAIT":  # 🔥 НОВАЯ ОБРАБОТКА ФЛУДА!
                        logger.error(
                            f"[{self.chat_thread.parent.profile_name}]-[Поток-{chat_id}]-[{self.chat_thread.chat_link}]-[{self.current_account_name}] 🚫 ПОЛУЧЕН ФЛУД - ЗАВЕРШАЕМ АККАУНТ")

                        # Добавляем в множество флуд аккаунтов
                        self.chat_thread.parent.flood_accounts.add(self.current_account_name)
                        self.chat_thread.parent._mark_account_as_processed(self.current_account_name, "флуд лимит")

                        # Обновляем статус в менеджере
                        await self._update_account_status_in_manager("flood")

                        should_block_chat = self.chat_thread.parent.chat_protection_manager.check_chat_protection(
                            self.chat_thread.chat_link,
                            self.current_account_name,
                            "flood"
                        )

                        if should_block_chat:
                            logger.error(
                                f"[{self.chat_thread.parent.profile_name}]-[Поток-{chat_id}]-"
                                f"[{self.chat_thread.chat_link}]-[{self.current_account_name}] "
                                f"🚫 ЧАТ ЗАБЛОКИРОВАН после флуда"
                            )
                            self.chat_thread.stop_chat_flag.set()

                        # Отключаемся и завершаем
                        await self._ensure_disconnected()
                        await self._handle_problem("flood")
                        break  # 🔥 ВЫХОДИМ ИЗ ЦИКЛА - аккаунт завершен!

                    elif result == "CRITICAL_FLOOD":  # 🔥 НОВАЯ ОБРАБОТКА КРИТИЧЕСКОГО ФЛУДА!
                        logger.error(
                            f"[{self.chat_thread.parent.profile_name}]-[Поток-{chat_id}]-[{self.chat_thread.chat_link}]-[{self.current_account_name}] "
                            f"🚨 КРИТИЧЕСКИЙ ФЛУД С ТАЙМАУТОМ - БЛОКИРУЕМ ЧАТ НЕМЕДЛЕННО!")

                        # 🚨 БЛОКИРУЕМ ЧАТ СРАЗУ БЕЗ СЧЕТЧИКОВ!
                        self._block_chat_immediately("Критический FloodWait с указанием времени ожидания")

                        # Добавляем аккаунт в флуд аккаунты
                        self.chat_thread.parent.flood_accounts.add(self.current_account_name)
                        self.chat_thread.parent._mark_account_as_processed(self.current_account_name,
                                                                           "критический флуд")

                        # Обновляем статус в менеджере
                        await self._update_account_status_in_manager("flood")

                        # Отключаемся и завершаем
                        await self._ensure_disconnected()
                        await self._handle_problem("flood")
                        break  # 🔥 ВЫХОДИМ ИЗ ЦИКЛА - аккаунт завершен!

                    elif result == "WRITEOFF":
                        logger.warning(
                            f"[{self.chat_thread.parent.profile_name}]-[Поток-{chat_id}]-[{self.chat_thread.chat_link}]-[{self.current_account_name}] ❌ СПИСАНИЕ (не добавлен): @{user.username}")

                        should_finish = self.chat_thread.parent._check_account_error_limits(self.current_account_name,
                                                                                            "writeoff")
                        if should_finish:
                            logger.error(
                                f"[{self.chat_thread.parent.profile_name}]-[Поток-{chat_id}]-[{self.chat_thread.chat_link}]-[{self.current_account_name}] 🔥 ПРЕВЫШЕН ЛИМИТ СПИСАНИЙ - завершаем аккаунт")

                            self.chat_thread.parent.writeoff_accounts.add(self.current_account_name)
                            self.chat_thread.parent._mark_account_as_processed(self.current_account_name,
                                                                               "лимит списаний")
                            await self._update_account_status_in_manager("writeoff")

                            should_block_chat = self.chat_thread.parent.chat_protection_manager.check_chat_protection(
                                self.chat_thread.chat_link,
                                self.current_account_name,
                                "writeoff_limit"
                            )

                            if should_block_chat:
                                logger.error(
                                    f"[{self.chat_thread.parent.profile_name}]-[Поток-{chat_id}]-"
                                    f"[{self.chat_thread.chat_link}]-[{self.current_account_name}] "
                                    f"🚫 ЧАТ ЗАБЛОКИРОВАН после превышения лимита списаний"
                                )
                                self.chat_thread.stop_chat_flag.set()

                            await self._ensure_disconnected()
                            await self._handle_problem("writeoff_limit")
                            break

                        self.chat_thread.parent.update_account_stats(self.current_account_name, error=True)

                    elif result == "SPAM_BLOCK":
                        logger.warning(
                            f"[{self.chat_thread.parent.profile_name}]-[Поток-{chat_id}]-[{self.chat_thread.chat_link}]-[{self.current_account_name}] 🚫 СПАМ-БЛОК: @{user.username}")

                        should_finish = self.chat_thread.parent._check_account_error_limits(self.current_account_name,
                                                                                            "spam_block")
                        if should_finish:
                            logger.error(
                                f"[{self.chat_thread.parent.profile_name}]-[Поток-{chat_id}]-[{self.chat_thread.chat_link}]-[{self.current_account_name}] 🔥 ПРЕВЫШЕН ЛИМИТ СПАМ-БЛОКОВ - завершаем аккаунт")

                            self.chat_thread.parent.spam_block_accounts.add(self.current_account_name)
                            self.chat_thread.parent._mark_account_as_processed(self.current_account_name,
                                                                               "лимит спам-блоков")
                            await self._update_account_status_in_manager("spam_block")

                            should_block_chat = self.chat_thread.parent.chat_protection_manager.check_chat_protection(
                                self.chat_thread.chat_link,
                                self.current_account_name,
                                "spam_limit"
                            )

                            if should_block_chat:
                                logger.error(
                                    f"[{self.chat_thread.parent.profile_name}]-[Поток-{chat_id}]-"
                                    f"[{self.chat_thread.chat_link}]-[{self.current_account_name}] "
                                    f"🚫 ЧАТ ЗАБЛОКИРОВАН после превышения лимита спам-блоков"
                                )
                                self.chat_thread.stop_chat_flag.set()

                            await self._ensure_disconnected()
                            await self._handle_problem("spam_limit")
                            break

                        self.chat_thread.parent.update_account_stats(self.current_account_name, spam_block=True,
                                                                     error=True)

                    elif result == "BLOCK_INVITE":
                        logger.warning(
                            f"[{self.chat_thread.parent.profile_name}]-[Поток-{chat_id}]-[{self.chat_thread.chat_link}]-[{self.current_account_name}] 🔐 БЛОК НА ИНВАЙТЫ: @{user.username}")

                        should_finish = self.chat_thread.parent._check_account_error_limits(self.current_account_name,
                                                                                            "block_invite")
                        if should_finish:
                            logger.error(
                                f"[{self.chat_thread.parent.profile_name}]-[Поток-{chat_id}]-[{self.chat_thread.chat_link}]-[{self.current_account_name}] 🔥 ПРЕВЫШЕН ЛИМИТ БЛОКОВ ИНВАЙТОВ - завершаем аккаунт")

                            self.chat_thread.parent.block_invite_accounts.add(self.current_account_name)
                            self.chat_thread.parent._mark_account_as_processed(self.current_account_name,
                                                                               "лимит блоков инвайтов")
                            await self._update_account_status_in_manager("dead")

                            should_block_chat = self.chat_thread.parent.chat_protection_manager.check_chat_protection(
                                self.chat_thread.chat_link,
                                self.current_account_name,
                                "block_limit"
                            )

                            if should_block_chat:
                                logger.error(
                                    f"[{self.chat_thread.parent.profile_name}]-[Поток-{chat_id}]-"
                                    f"[{self.chat_thread.chat_link}]-[{self.current_account_name}] "
                                    f"🚫 ЧАТ ЗАБЛОКИРОВАН после превышения лимита блоков инвайтов"
                                )
                                self.chat_thread.stop_chat_flag.set()

                            await self._ensure_disconnected()
                            await self._handle_problem("block_limit")
                            break

                        self.chat_thread.parent.update_account_stats(self.current_account_name, error=True)

                    elif result == "PRIVACY":
                        logger.warning(
                            f"[{self.chat_thread.parent.profile_name}]-[Поток-{chat_id}]-[{self.chat_thread.chat_link}]-[{self.current_account_name}] 🔒 ПРИВАТНЫЕ ОГРАНИЧЕНИЯ: @{user.username}")

                    elif result == "NOT_FOUND":
                        logger.warning(
                            f"[{self.chat_thread.parent.profile_name}]-[Поток-{chat_id}]-[{self.chat_thread.chat_link}]-[{self.current_account_name}] 🔍 ПОЛЬЗОВАТЕЛЬ НЕ НАЙДЕН: @{user.username}")

                    elif result == "USER_ALREADY_CHATS":
                        logger.warning(
                            f"[{self.chat_thread.parent.profile_name}]-[Поток-{chat_id}]-[{self.chat_thread.chat_link}]-[{self.current_account_name}] 👤 ПОЛЬЗОВАТЕЛЬ УЖЕ СОСТОИТ В БОЛЬШОМ КОЛИЧЕСТВЕ ГРУПП: @{user.username}")

                    elif result == "USER_ALREADY":
                        logger.info(
                            f"[{self.chat_thread.parent.profile_name}]-[Поток-{chat_id}]-[{self.chat_thread.chat_link}]-[{self.current_account_name}] 👤 УЖЕ ОБРАБОТАН: @{user.username}")

                    else:  # ERROR и прочие ошибки
                        logger.warning(
                            f"[{self.chat_thread.parent.profile_name}]-[Поток-{chat_id}]-[{self.chat_thread.chat_link}]-[{self.current_account_name}] ❓ ОШИБКА: @{user.username} (результат: {result})")

                except (AuthKeyUnregisteredError, SessionRevokedError) as e:
                    # Критические ошибки соединения - НЕ флуд!
                    logger.error(
                        f"[{self.chat_thread.parent.profile_name}]-[Поток-{chat_id}]-[{self.chat_thread.chat_link}]-[{self.current_account_name}] 💥 КРИТИЧЕСКАЯ ОШИБКА: {e}")

                    user.status = UserStatus.ERROR
                    user.last_attempt = datetime.now()
                    user.error_message = str(e)

                    # КРИТИЧНО: НЕМЕДЛЕННО обновляем статус
                    if self.realtime_logger:
                        self.realtime_logger.update_user_status_immediately(user)

                    self.chat_thread.parent.processed_users[user.username] = user

                    problem_type = 'dead'  # Критические ошибки = мертвый аккаунт
                    self.chat_thread.parent._mark_account_as_processed(self.current_account_name,
                                                                       f"критическая ошибка: {problem_type}")

                    await self._update_account_status_in_manager(problem_type)
                    await self._ensure_disconnected()
                    await self._handle_problem(problem_type)
                    break

                # Задержка между инвайтами
                if self.chat_thread.parent.config.delay_between > 0:
                    await asyncio.sleep(self.chat_thread.parent.config.delay_between)

            # 6. 🔥 ИСПРАВЛЕНО: Отзыв прав через персональную очередь
            if rights_granted:
                await self._revoke_rights(user_entity.id, username_thread_account)

            # 7. ПОКАЗЫВАЕМ СТАТИСТИКУ ПРИ ЗАВЕРШЕНИИ АККАУНТА
            self._show_account_finish_stats("ЗАВЕРШИЛ РАБОТУ", invites_count)

            # 8. Финализация аккаунта
            await self._finalize_current_account(client_connected)

            # Аккаунт успешно завершен - можем переходить к следующему
            return True

        except Exception as e:
            logger.error(
                f"[{self.chat_thread.parent.profile_name}]-[Поток-{chat_id}]-[{self.chat_thread.chat_link}]-[{self.current_account_name}] 💥 Критическая ошибка: {e}")

            # Помечаем аккаунт
            self.chat_thread.parent._mark_account_as_processed(self.current_account_name,
                                                               f"критическая ошибка: {str(e)[:50]}")

            await self._handle_problem("dead")
            await self._finalize_current_account(client_connected)

            # При критической ошибке переходим к следующему аккаунту
            return True

    async def _invite_user(self, user: InviteUser) -> str:
        """
        ОПТИМИЗИРОВАННЫЙ инвайт пользователя с системой реального времени
        🔥 ОБНОВЛЕНО: Новая логика FloodWait - НЕ ЖДЕМ 300 секунд!
        Возвращает: SUCCESS, WRITEOFF, SPAM_BLOCK, BLOCK_INVITE, PRIVACY, NOT_FOUND, USER_ALREADY, ERROR, FLOOD_WAIT
        """
        client = self.thread_account.client
        username = user.username.lstrip('@')

        # Проверяем, не обрабатывали ли мы уже этого пользователя
        if username in self.chat_thread.parent.processed_users:
            existing_user = self.chat_thread.parent.processed_users[username]
            # Если пользователь уже был успешно приглашен или имеет финальный статус, пропускаем
            if existing_user.status in [UserStatus.INVITED, UserStatus.ALREADY_IN, UserStatus.NOT_FOUND]:
                return "USER_ALREADY"

        try:
            # Проверяем пользователя
            try:
                full_user = await client(GetFullUserRequest(username))
                old_common_chats = full_user.full_user.common_chats_count
            except (ValueError, TypeError, UsernameInvalidError, UsernameNotOccupiedError):
                user.status = UserStatus.NOT_FOUND
                user.last_attempt = datetime.now()
                user.error_message = "Пользователь не найден"
                user.chat_link = self.chat_thread.chat_link

                # КРИТИЧНО: НЕМЕДЛЕННО обновляем статус
                if self.realtime_logger:
                    self.realtime_logger.update_user_status_immediately(user)

                self.chat_thread.parent.processed_users[username] = user
                return "NOT_FOUND"

            # Проверяем не находится ли пользователь уже в этом чате
            if old_common_chats > 0:
                try:
                    user_entity = await client.get_input_entity(username)
                    common_chats_result = await client(GetCommonChatsRequest(
                        user_id=user_entity,
                        max_id=0,
                        limit=100
                    ))

                    current_chat_entity = await client.get_input_entity(self.chat_thread.chat_link)
                    current_chat_id = None

                    try:
                        chat_full = await client.get_entity(self.chat_thread.chat_link)
                        current_chat_id = chat_full.id
                    except Exception as e:
                        pass

                    if current_chat_id:
                        for chat in common_chats_result.chats:
                            if hasattr(chat, 'id') and chat.id == current_chat_id:
                                user.status = UserStatus.ALREADY_IN
                                user.last_attempt = datetime.now()
                                user.error_message = "Уже в чате"
                                user.chat_link = self.chat_thread.chat_link

                                # КРИТИЧНО: НЕМЕДЛЕННО обновляем статус
                                if self.realtime_logger:
                                    self.realtime_logger.update_user_status_immediately(user)

                                self.chat_thread.parent.processed_users[username] = user
                                return "USER_ALREADY"

                except Exception as e:
                    # Если не удалось проверить - продолжаем инвайт
                    pass

            # Инвайт через админские права
            input_channel = await client.get_input_entity(self.chat_thread.chat_link)
            input_user = await client.get_input_entity(username)

            rights = ChatAdminRights(
                invite_users=True,
                anonymous=True,
            )

            await client(EditAdminRequest(
                channel=input_channel,
                user_id=input_user,
                admin_rights=rights,
                rank="админ"
            ))

            await asyncio.sleep(15)

            no_rights = ChatAdminRights(
                invite_users=False,
                anonymous=False,
            )

            # Забираем права через главного админа
            await client(EditAdminRequest(
                channel=input_channel,
                user_id=input_user,
                admin_rights=no_rights,
                rank=""
            ))

            # Проверяем успешность
            await asyncio.sleep(15)

            try:
                full_user2 = await client(GetFullUserRequest(username))
                new_common_chats = full_user2.full_user.common_chats_count

                if new_common_chats <= old_common_chats:
                    user.status = UserStatus.ERROR
                    user.last_attempt = datetime.now()
                    user.error_message = "Списание"

                    # КРИТИЧНО: НЕМЕДЛЕННО обновляем статус
                    if self.realtime_logger:
                        self.realtime_logger.update_user_status_immediately(user)

                    self.chat_thread.parent.processed_users[username] = user
                    return "WRITEOFF"
            except:
                pass

            # ✅ УСПЕХ - САМОЕ ВАЖНОЕ МЕСТО!
            user.status = UserStatus.INVITED
            user.last_attempt = datetime.now()
            user.error_message = "Успешно приглашен"
            user.chat_link = self.chat_thread.chat_link

            # КРИТИЧНО: НЕМЕДЛЕННО обновляем статус и логируем успех
            if self.realtime_logger:
                self.realtime_logger.update_user_status_immediately(user)
                self.realtime_logger.log_successful_invite(
                    username=username,
                    chat_link=self.chat_thread.chat_link,
                    account_name=self.current_account_name
                )

            self.chat_thread.parent.processed_users[username] = user
            self.thread_account.increment_green_people()
            return "SUCCESS"


        except (PeerFloodError, FloodWaitError) as e:

            # 🔥 НОВАЯ ЛОГИКА - ПРОВЕРЯЕМ ЕСТЬ ЛИ УПОМИНАНИЕ ВРЕМЕНИ ОЖИДАНИЯ!
            error_msg = str(e).lower()
            # Проверяем есть ли в сообщении "wait of X seconds" - ЛЮБОЕ число!
            import re
            wait_match = re.search(r'wait of (\d+) seconds', error_msg)
            # 🚨 ЕСЛИ ЕСТЬ УПОМИНАНИЕ ВРЕМЕНИ - ЭТО КРИТИЧЕСКИЙ ФЛУД!
            if wait_match:

                wait_seconds = int(wait_match.group(1))
                user.status = UserStatus.FLOOD_WAIT
                user.last_attempt = datetime.now()
                user.error_message = f"КРИТИЧЕСКИЙ FloodWait: {wait_seconds} секунд"
                user.chat_link = self.chat_thread.chat_link
                # КРИТИЧНО: НЕМЕДЛЕННО обновляем статус
                if self.realtime_logger:
                    self.realtime_logger.update_user_status_immediately(user)
                self.chat_thread.parent.processed_users[username] = user
                # 🚨 КРИТИЧЕСКИЙ ФЛУД - БЛОКИРУЕМ ЧАТ СРАЗУ!
                logger.error(
                    f"[{self.chat_thread.parent.profile_name}]-[Поток-{self.chat_thread.chat_id}]-[{self.chat_thread.chat_link}]-[{self.current_account_name}] "
                    f"🚨 КРИТИЧЕСКИЙ ФЛУД {wait_seconds} секунд - БЛОКИРУЕМ ЧАТ НЕМЕДЛЕННО!")

                return "CRITICAL_FLOOD"  # 🔥 НОВЫЙ тип результата!
            else:

                # 🔥 ОБЫЧНЫЙ ФЛУД БЕЗ ВРЕМЕНИ - только завершаем аккаунт
                user.status = UserStatus.FLOOD_WAIT
                user.last_attempt = datetime.now()
                user.error_message = f"Обычный FloodWait: {str(e)}"
                user.chat_link = self.chat_thread.chat_link
                # КРИТИЧНО: НЕМЕДЛЕННО обновляем статус
                if self.realtime_logger:
                    self.realtime_logger.update_user_status_immediately(user)
                self.chat_thread.parent.processed_users[username] = user
                # ВАЖНО: Логируем но НЕ ЖДЕМ!
                logger.error(
                    f"[{self.chat_thread.parent.profile_name}]-[Поток-{self.chat_thread.chat_id}]-[{self.chat_thread.chat_link}]-[{self.current_account_name}] "
                    f"🚫 ПОЛУЧЕН ОБЫЧНЫЙ ФЛУД - ЗАВЕРШАЕМ АККАУНТ: {str(e)}")

                return "FLOOD_WAIT"

        except UserPrivacyRestrictedError:
            user.status = UserStatus.PRIVACY
            user.last_attempt = datetime.now()
            user.error_message = "Приватные ограничения"
            user.chat_link = self.chat_thread.chat_link

            # КРИТИЧНО: НЕМЕДЛЕННО обновляем статус
            if self.realtime_logger:
                self.realtime_logger.update_user_status_immediately(user)

            self.chat_thread.parent.processed_users[username] = user
            return "PRIVACY"

        except (UserDeactivatedBanError, UserDeactivatedError):
            user.status = UserStatus.NOT_FOUND
            user.last_attempt = datetime.now()
            user.error_message = "Пользователь деактивирован"
            user.chat_link = self.chat_thread.chat_link

            # КРИТИЧНО: НЕМЕДЛЕННО обновляем статус
            if self.realtime_logger:
                self.realtime_logger.update_user_status_immediately(user)

            self.chat_thread.parent.processed_users[username] = user
            return "NOT_FOUND"

        except Exception as e:
            error_msg = str(e)

            if "You're spamreported, you can't create channels or chats" in error_msg:
                user.status = UserStatus.SPAM_BLOCK
                user.last_attempt = datetime.now()
                user.error_message = "Спамблок"
                user.chat_link = self.chat_thread.chat_link

                # КРИТИЧНО: НЕМЕДЛЕННО обновляем статус
                if self.realtime_logger:
                    self.realtime_logger.update_user_status_immediately(user)

                self.chat_thread.parent.processed_users[username] = user
                return "SPAM_BLOCK"

            elif "One of the users you tried to add is already in too many channels/supergroups" in error_msg:
                user.status = UserStatus.USER_ALREADY_CHATS
                user.last_attempt = datetime.now()
                user.error_message = "Юзер_уже_в_большом_количестве_групп"
                user.chat_link = self.chat_thread.chat_link

                # КРИТИЧНО: НЕМЕДЛЕННО обновляем статус
                if self.realtime_logger:
                    self.realtime_logger.update_user_status_immediately(user)

                self.chat_thread.parent.processed_users[username] = user
                return "USER_ALREADY_CHATS"

            elif "The provided user is not a mutual contact" in error_msg:
                user.status = UserStatus.PRIVACY
                user.last_attempt = datetime.now()
                user.error_message = "Приватные ограничения"
                user.chat_link = self.chat_thread.chat_link

                # КРИТИЧНО: НЕМЕДЛЕННО обновляем статус
                if self.realtime_logger:
                    self.realtime_logger.update_user_status_immediately(user)

                self.chat_thread.parent.processed_users[username] = user
                return "PRIVACY"

            else:
                user.status = UserStatus.ERROR
                user.last_attempt = datetime.now()
                user.error_message = f"Ошибка: {str(e)[:50]}"
                user.chat_link = self.chat_thread.chat_link

                # КРИТИЧНО: НЕМЕДЛЕННО обновляем статус
                if self.realtime_logger:
                    self.realtime_logger.update_user_status_immediately(user)

                self.chat_thread.parent.processed_users[username] = user
                print(e)
                return "BLOCK_INVITE"

    def _count_accounts_used_in_chat(self) -> int:
        """Подсчитывает аккаунты использованные ИМЕННО В ЭТОМ ЧАТЕ"""
        return len(self.chat_thread.chat_accounts_used)

    async def _finalize_current_account(self, client_connected: bool):
        """🔥 ОБНОВЛЕНО: Финализация текущего аккаунта С ПРОВЕРКОЙ ОТКЛЮЧЕНИЯ"""
        try:
            # ОБЯЗАТЕЛЬНОЕ отключение
            await self._ensure_disconnected()

            # Освобождение в менеджере
            try:
                self.chat_thread.parent.account_manager.release_account(self.current_account_name, self.module_name)
            except Exception as e:
                logger.error(
                    f"[{self.chat_thread.parent.profile_name}]-[{self.current_account_name}] Ошибка освобождения: {e}")

            # Перемещение файлов - ДОБАВЛЯЕМ ПОДДЕРЖКУ ФЛУД АККАУНТОВ
            if (self.current_account_name in self.chat_thread.parent.writeoff_accounts or
                    self.current_account_name in self.chat_thread.parent.spam_block_accounts or
                    self.current_account_name in self.chat_thread.parent.block_invite_accounts or
                    self.current_account_name in self.chat_thread.parent.finished_successfully_accounts or
                    self.current_account_name in self.chat_thread.parent.frozen_accounts or
                    self.current_account_name in self.chat_thread.parent.blocked_accounts or
                    self.current_account_name in self.chat_thread.parent.flood_accounts):  # 🔥 НОВОЕ УСЛОВИЕ!

                try:
                    # Определяем тип папки - ДОБАВЛЯЕМ ФЛУД!
                    if self.current_account_name in self.chat_thread.parent.writeoff_accounts:
                        problem_type = 'writeoff'
                    elif self.current_account_name in self.chat_thread.parent.spam_block_accounts:
                        problem_type = 'spam_block'
                    elif self.current_account_name in self.chat_thread.parent.block_invite_accounts:
                        problem_type = 'block_invite'
                    elif self.current_account_name in self.chat_thread.parent.finished_successfully_accounts:
                        problem_type = 'finished'
                    elif self.current_account_name in self.chat_thread.parent.frozen_accounts:
                        problem_type = 'frozen'
                    elif self.current_account_name in self.chat_thread.parent.flood_accounts:  # 🔥 НОВАЯ ЛОГИКА!
                        problem_type = 'flood'
                    else:
                        problem_type = 'dead'

                    success = self.chat_thread.parent.account_mover.move_account(self.current_account_name,
                                                                                 problem_type)

                    if success:
                        logger.debug(
                            f"[{self.chat_thread.parent.profile_name}]-[{self.current_account_name}] 📁 Файлы перемещены в папку: {problem_type}")
                    else:
                        logger.warning(
                            f"[{self.chat_thread.parent.profile_name}]-[{self.current_account_name}] ⚠️ Не удалось переместить файлы")

                except Exception as e:
                    logger.error(
                        f"[{self.chat_thread.parent.profile_name}]-[{self.current_account_name}] Ошибка перемещения файлов: {e}")

        except Exception as e:
            logger.error(
                f"[{self.chat_thread.parent.profile_name}]-[{self.current_account_name}] Ошибка финализации: {e}")

    async def _update_account_status_in_manager(self, new_status: str):
        """🔥 ОБНОВЛЕНО: Обновляет статус и путь аккаунта в менеджере"""
        try:
            # Получаем account_data из менеджера
            if hasattr(self.chat_thread.parent.account_manager, 'traffic_accounts'):
                if self.current_account_name in self.chat_thread.parent.account_manager.traffic_accounts:
                    account_data = self.chat_thread.parent.account_manager.traffic_accounts[self.current_account_name]

                    old_status = account_data.status
                    account_data.status = new_status

                    # Освобождаем аккаунт в менеджере
                    account_data.is_busy = False
                    account_data.busy_by = None

                    # Обновляем пути к файлам после перемещения
                    from paths import WORK_TRAFFER_FOLDER
                    folder_mapping = {
                        'writeoff': WORK_TRAFFER_FOLDER / "Списанные",
                        'spam_block': WORK_TRAFFER_FOLDER / "Спам_блок",
                        'block_invite': WORK_TRAFFER_FOLDER / "Блок_инвайтов",
                        'frozen': WORK_TRAFFER_FOLDER / "Замороженные",
                        'dead': WORK_TRAFFER_FOLDER / "Мертвые",
                        'finished': WORK_TRAFFER_FOLDER / "Успешно_отработанные",
                        'flood': WORK_TRAFFER_FOLDER / "Флуд"  # 🔥 НОВОЕ MAPPING для флуда
                    }

                    if new_status in folder_mapping:
                        new_folder = folder_mapping[new_status]
                        # Обновляем пути в account_data
                        account_data.account.session_path = new_folder / f"{self.current_account_name}.session"
                        account_data.account.json_path = new_folder / f"{self.current_account_name}.json"

        except Exception as e:
            logger.error(
                f"[{self.chat_thread.parent.profile_name}]-[Поток-{self.chat_thread.chat_id}]-[{self.chat_thread.chat_link}]-[{self.current_account_name}] Ошибка обновления статуса в менеджере: {e}")

    def _show_account_finish_stats(self, reason: str, account_invites: int = 0):
        """Статистика ТОЛЬКО ПО ЭТОМУ ЧАТУ"""
        try:
            chat_link = self.chat_thread.chat_link

            # Берем данные ИМЕННО ПО ЭТОМУ ЧАТУ
            chat_success = self.chat_thread.chat_success
            chat_total = self.chat_thread.chat_total
            accounts_used = len(self.chat_thread.chat_accounts_used)

            users_remaining = self.chat_thread.parent.user_queue.qsize()
            total_users = getattr(self.chat_thread.parent, 'total_users_count', users_remaining + chat_total)

            logger.success(
                f"💼 СТАТИСТИКА ЧАТА {chat_link}: ✅ Успешных: {chat_success}, 📝 Попыток: {chat_total}, 👥 Аккаунтов: {accounts_used}, 📊 Осталось: {users_remaining}/{total_users}")

        except Exception as e:
            logger.error(f"Ошибка статистики чата: {e}")

    async def _join_chat(self):
        """Вход в чат"""
        try:
            result = await self.thread_account.join(self.chat_thread.chat_link)

            if result == "ALREADY_PARTICIPANT":
                logger.success(
                    f"[{self.chat_thread.parent.profile_name}]-[Поток-{self.chat_thread.chat_id}]-[{self.chat_thread.chat_link}]-[{self.current_account_name}] Уже в чате")
                return "SUCCESS"
            elif result == "FROZEN_ACCOUNT":
                return "FROZEN_ACCOUNT"
            elif result == "CHAT_NOT_FOUND":
                return "CHAT_NOT_FOUND"
            elif isinstance(result, str) and result.startswith("ERROR:"):
                return "ERROR"
            else:
                logger.info(
                    f"[{self.chat_thread.parent.profile_name}]-[Поток-{self.chat_thread.chat_id}]-[{self.chat_thread.chat_link}]-[{self.current_account_name}] Вступил в чат")
                return "SUCCESS"

        except Exception as e:
            logger.error(
                f"[{self.chat_thread.parent.profile_name}]-[Поток-{self.chat_thread.chat_id}]-[{self.chat_thread.chat_link}]-[{self.current_account_name}] Ошибка входа в чат: {e}")
            return "ERROR"

    async def _revoke_rights(self, thread_user_id: int, username: str):
        """🔥 ИСПРАВЛЕНО: Отзыв прав через персональную очередь чата"""
        try:
            response_queue = queue.Queue()
            command = AdminCommand(
                action="REVOKE_RIGHTS",
                worker_name=self.current_account_name,
                worker_user_id=thread_user_id,
                worker_access_hash=0,
                chat_link=self.chat_thread.chat_link,
                response_queue=response_queue,
                username=username
            )

            # 🔥 КРИТИЧНО: Отправляем команду в персональную очередь ЭТОГО чата!
            admin_name = self.chat_thread.parent.chat_admins[self.chat_thread.chat_link].name

            self.chat_thread.parent.send_command_to_chat(self.chat_thread.chat_link, command)

            try:
                response_queue.get(timeout=600)
                logger.info(
                    f"[{self.chat_thread.parent.profile_name}]-[Поток-{self.chat_thread.chat_id}]-[{self.chat_thread.chat_link}]-[{self.current_account_name}] ✅ Права отозваны админом {admin_name}")
            except queue.Empty:
                logger.warning(
                    f"[{self.chat_thread.parent.profile_name}]-[Поток-{self.chat_thread.chat_id}]-[{self.chat_thread.chat_link}]-[{self.current_account_name}] ⚠️ Таймаут отзыва прав у админа {admin_name}")

        except Exception as e:
            logger.error(
                f"[{self.chat_thread.parent.profile_name}]-[Поток-{self.chat_thread.chat_id}]-[{self.chat_thread.chat_link}]-[{self.current_account_name}] ❌ Ошибка отзыва прав: {e}")

    async def _ensure_disconnected(self):
        """ПРИНУДИТЕЛЬНОЕ отключение от Telethon с проверкой"""
        try:
            if self.thread_account and self.thread_account.client:
                if hasattr(self.thread_account.client, 'is_connected') and self.thread_account.client.is_connected():
                    await self.thread_account.disconnect()
                else:
                    logger.debug(f"[{self.current_account_name}] Аккаунт уже отключен")
            else:
                logger.debug(f"[{self.current_account_name}] Клиент не существует")
        except Exception as e:
            logger.warning(f"[{self.current_account_name}] Ошибка при принудительном отключении (игнорируем): {e}")
            # Игнорируем ошибки отключения - главное что мы попытались

    async def _disconnect(self):
        """МЯГКОЕ отключение потока"""
        await self._ensure_disconnected()

    async def _handle_problem(self, problem_type: str):
        """🔥 ОБНОВЛЕНО: Обработка проблемы С ОБЯЗАТЕЛЬНЫМ ОТКЛЮЧЕНИЕМ"""
        try:
            # СНАЧАЛА отключаем
            await self._ensure_disconnected()

            # Потом помечаем как обработанный
            self.chat_thread.parent._mark_account_as_processed(self.current_account_name, problem_type)

            if problem_type in ['frozen', 'spam_limit']:
                self.chat_thread.parent.frozen_accounts.add(self.current_account_name)
            elif problem_type == 'flood':  # 🔥 НОВАЯ ОБРАБОТКА ФЛУДА!
                self.chat_thread.parent.flood_accounts.add(self.current_account_name)
            else:
                self.chat_thread.parent.blocked_accounts.add(self.current_account_name)

        except Exception as e:
            logger.error(
                f"[{self.chat_thread.parent.profile_name}]-[Поток-{self.chat_thread.chat_id}]-[{self.chat_thread.chat_link}]-[{self.current_account_name}] Ошибка пометки: {e}")