# src/modules/impl/inviter/admin_inviter.py
"""
Инвайтер через админку - использует бота для управления правами админов
ОБНОВЛЕННАЯ ВЕРСИЯ с интеграцией BotManager и AdminRightsManager
"""

import threading
import asyncio
import queue
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from loguru import logger
from pathlib import Path

from .base_inviter import BaseInviterProcess
from .bot_manager import BotManager
from .admin_rights_manager import AdminRightsManager
from src.entities.moduls.inviter import InviteUser, UserStatus, AccountStats

# Импорты Telethon для инвайтов
from telethon.tl.functions.channels import InviteToChannelRequest
from telethon.tl.functions.users import GetFullUserRequest
from telethon.tl.functions.messages import GetCommonChatsRequest
from telethon.errors import (
    UsernameInvalidError, UsernameNotOccupiedError,
    PeerFloodError, FloodWaitError,
    UserPrivacyRestrictedError, UserNotMutualContactError,
    ChatAdminRequiredError, ChatWriteForbiddenError,
    UsersTooMuchError, ChannelsTooMuchError,
    UserDeactivatedBanError, UserDeactivatedError,
    AuthKeyUnregisteredError, SessionRevokedError,
    ChannelPrivateError, ChannelInvalidError
)


class AdminInviterProcess(BaseInviterProcess):
    """Инвайтер через админку - один поток на чат с управлением админ-правами"""

    def __init__(self, profile_name: str, profile_data: Dict, account_manager):
        super().__init__(profile_name, profile_data, account_manager)

        # Токен бота из конфигурации профиля
        self.bot_token = profile_data.get('config', {}).get('bot_token')
        if not self.bot_token:
            logger.error(f"❌ Не указан токен бота в профиле {profile_name}")

        # Главный админ аккаунт из конфигурации
        self.main_admin_account_name = profile_data.get('config', {}).get('main_admin_account')
        if not self.main_admin_account_name:
            logger.error(f"❌ Не указан главный админ аккаунт в профиле {profile_name}")

        # Менеджеры
        self.bot_manager: Optional[BotManager] = None
        self.admin_rights_manager: Optional[AdminRightsManager] = None

        # Потоки для чатов
        self.chat_threads = []

        # Статистика по аккаунтам (как в классическом)
        self.account_stats: Dict[str, AccountStats] = {}
        self.total_success = 0
        self.total_errors = 0
        self.total_processed = 0
        self.frozen_accounts = set()
        self.finished_accounts = set()
        self.account_finish_times: Dict[str, datetime] = {}
        self.initial_chats_count = 0

        logger.info(f"🤖 Инициализирован админ-инвайтер для {profile_name}")
        if self.main_admin_account_name:
            logger.info(f"   Главный админ: {self.main_admin_account_name}")

    def _run_inviting(self):
        """Основная логика инвайтинга через админку"""
        logger.info(f"[{self.profile_name}] 🤖 Запуск инвайтинга через админку")

        if not self.bot_token:
            logger.error(f"[{self.profile_name}] ❌ Не настроен токен бота!")
            return

        if not self.main_admin_account_name:
            logger.error(f"[{self.profile_name}] ❌ Не настроен главный админ аккаунт!")
            return

        try:
            # Запускаем асинхронную логику
            asyncio.run(self._async_run_inviting())
        except Exception as e:
            logger.error(f"[{self.profile_name}] ❌ Критическая ошибка: {e}")
        finally:
            self.is_running = False
            self.finished_at = datetime.now()

    async def _async_run_inviting(self):
        """Асинхронная часть логики инвайтинга"""
        try:
            # 1. Инициализируем бот-менеджер
            if not await self._initialize_bot():
                logger.error(f"[{self.profile_name}] ❌ Не удалось инициализировать бота")
                return

            # 2. Взаимодействие с пользователем для настройки бота
            if not await self._user_interaction():
                logger.error(f"[{self.profile_name}] ❌ Настройка отменена пользователем")
                return

            # 3. Запускаем синхронную часть (потоки для чатов)
            await self._start_chat_threads()

        except Exception as e:
            logger.error(f"[{self.profile_name}] ❌ Ошибка в асинхронном процессе: {e}")
        finally:
            # Закрываем соединения
            if self.bot_manager:
                await self.bot_manager.disconnect()

    async def _initialize_bot(self) -> bool:
        """Инициализирует бот-менеджер"""
        try:
            logger.info(f"[{self.profile_name}] 🤖 Инициализация бота...")

            # Получаем прокси если настроены
            proxy_url = None
            # TODO: Добавить получение прокси из конфигурации если нужно

            # Создаем бот-менеджер
            self.bot_manager = BotManager(
                bot_token=self.bot_token,
                proxy_url=proxy_url
            )

            # Подключаемся к боту
            if not await self.bot_manager.connect():
                logger.error(f"[{self.profile_name}] ❌ Не удалось подключиться к боту")
                return False

            # Создаем менеджер админ-прав
            self.admin_rights_manager = AdminRightsManager(
                bot_manager=self.bot_manager
            )

            logger.info(f"✅ Бот инициализирован: @{self.bot_manager.bot_username}")
            return True

        except Exception as e:
            logger.error(f"❌ Ошибка инициализации бота: {e}")
            return False

    async def _user_interaction(self) -> bool:
        """Взаимодействие с пользователем для настройки бота"""
        try:
            # Получаем список чатов
            chat_links = []
            temp_queue = []

            while not self.chat_queue.empty():
                chat = self.chat_queue.get_nowait()
                chat_links.append(chat)
                temp_queue.append(chat)

            # Возвращаем чаты обратно в очередь
            for chat in temp_queue:
                self.chat_queue.put(chat)

            if not chat_links:
                logger.error("❌ Нет чатов для обработки")
                return False

            # Выводим инструкции
            logger.info(f"=" * 70)
            logger.info(f"🤖 ИНСТРУКЦИЯ ПО НАСТРОЙКЕ БОТА")
            logger.info(f"=" * 70)
            logger.info(f"1. Добавьте бота @{self.bot_manager.bot_username} в следующие чаты:")

            for i, chat in enumerate(chat_links, 1):
                logger.info(f"   {i}. {chat}")

            logger.info(f"2. Дайте боту права администратора во всех чатах")
            logger.info(f"   (Права: управление пользователями, управление админами)")
            logger.info(f"3. После завершения настройки работа продолжится автоматически")
            logger.info(f"=" * 70)

            # Проверяем статус бота в каждом чате
            logger.info(f"🔍 Проверяем статус бота в чатах...")
            setup_needed = []

            for chat in chat_links:
                is_admin = await self.bot_manager.check_bot_admin_status(chat)
                if not is_admin:
                    setup_needed.append(chat)
                    logger.warning(f"⚠️ Бот НЕ является админом в: {chat}")
                else:
                    logger.info(f"✅ Бот уже админ в: {chat}")

            if setup_needed:
                logger.info(f"⏳ Ожидаем настройку в {len(setup_needed)} чатах...")
                logger.info(f"   Чаты требующие настройки: {setup_needed}")

                # Ждем пока пользователь настроит
                await asyncio.sleep(60)

                # Повторная проверка
                logger.info(f"🔍 Повторная проверка статуса бота...")
                still_need_setup = []

                for chat in setup_needed:
                    is_admin = await self.bot_manager.check_bot_admin_status(chat)
                    if not is_admin:
                        still_need_setup.append(chat)

                if still_need_setup:
                    logger.warning(f"⚠️ Бот все еще не настроен в {len(still_need_setup)} чатах:")
                    for chat in still_need_setup:
                        logger.warning(f"   - {chat}")
                    logger.info(f"ℹ️ Продолжаем работу с настроенными чатами")

            logger.info(f"✅ Настройка завершена, продолжаем работу")
            return True

        except Exception as e:
            logger.error(f"❌ Ошибка взаимодействия с пользователем: {e}")
            return False

    async def _start_chat_threads(self):
        """Запускает потоки для чатов (синхронная часть как в классическом)"""
        # Задержка после старта
        if self.config.delay_after_start > 0:
            logger.info(f"[{self.profile_name}] Задержка {self.config.delay_after_start} сек...")
            self.stop_flag.wait(self.config.delay_after_start)

        # Получаем начальное количество чатов
        total_chats = self.chat_queue.qsize()
        self.initial_chats_count = total_chats
        logger.info(f"[{self.profile_name}] Всего чатов для обработки: {total_chats}")

        # Рассчитываем общее количество требуемых успешных инвайтов
        total_invites_needed = total_chats * self.config.success_per_chat if self.config.success_per_chat > 0 else 999999
        logger.info(f"[{self.profile_name}] Требуется успешных инвайтов всего: {total_invites_needed}")

        # Получаем главного админа
        module_name = f"admin_inviter_{self.profile_name}"
        main_admin_account = self.account_manager.get_account(self.main_admin_account_name, module_name)

        if not main_admin_account:
            logger.error(f"[{self.profile_name}] ❌ Не удалось получить главного админа: {self.main_admin_account_name}")
            return

        # Получаем воркеров
        max_workers_per_chat = self.config.threads_per_chat
        total_workers_needed = min(total_chats * max_workers_per_chat, self.account_manager.get_free_accounts_count())

        worker_accounts = self.account_manager.get_free_accounts(module_name, total_workers_needed)
        logger.info(f"[{self.profile_name}] Получено воркер-аккаунтов: {len(worker_accounts)}")

        # Создаем потоки для чатов
        chat_index = 0
        worker_index = 0

        while self.chat_queue.qsize() > 0 and not self.stop_flag.is_set():
            try:
                chat = self.chat_queue.get_nowait()

                # Выделяем воркеров для этого чата
                chat_workers = []
                workers_for_chat = min(max_workers_per_chat, len(worker_accounts) - worker_index)

                for j in range(workers_for_chat):
                    if worker_index < len(worker_accounts):
                        chat_workers.append(worker_accounts[worker_index].name)
                        worker_index += 1

                if not chat_workers:
                    # Возвращаем чат обратно
                    self.chat_queue.put(chat)
                    logger.warning(f"[{self.profile_name}] Нет воркеров для чата {chat}")
                    break

                # Создаем поток для чата
                thread = AdminChatWorkerThread(
                    chat_id=chat_index + 1,
                    chat_link=chat,
                    main_admin_account=self.main_admin_account_name,
                    worker_accounts=chat_workers,
                    parent=self,
                    profile_name=self.profile_name,
                    bot_manager=self.bot_manager,
                    admin_rights_manager=self.admin_rights_manager
                )
                thread.start()
                self.chat_threads.append(thread)
                chat_index += 1

                logger.info(
                    f"[{self.profile_name}] Запущен поток для чата #{chat_index}: {chat} "
                    f"(главный админ: {self.main_admin_account_name}, воркеров: {len(chat_workers)})"
                )

            except queue.Empty:
                break

        # Ждем завершения всех потоков
        self._wait_for_threads()

        # Обрабатываем отложенные чаты если остались
        if self.chat_queue.qsize() > 0:
            logger.warning(f"[{self.profile_name}] Остались необработанные чаты: {self.chat_queue.qsize()}")

        # Выводим итоговую статистику
        self._print_final_stats()

    def _get_fresh_accounts(self, module_name: str, count: int) -> List:
        """Получает свежие аккаунты (копия из классического)"""
        self._clean_expired_accounts()
        all_accounts = self.account_manager.get_free_accounts(module_name, count * 2)

        if not all_accounts:
            return []

        fresh_accounts = []
        for account in all_accounts:
            if account.name not in self.finished_accounts:
                fresh_accounts.append(account)
                if len(fresh_accounts) >= count:
                    break
            else:
                self.account_manager.release_account(account.name, module_name)
                logger.info(f"[{self.profile_name}] Аккаунт {account.name} отработан, пропускаем")

        return fresh_accounts

    def _clean_expired_accounts(self):
        """Очищает аккаунты с истекшей 24-часовой меткой"""
        now = datetime.now()
        expired = []

        for account_name, finish_time in self.account_finish_times.items():
            if now - finish_time >= timedelta(hours=24):
                expired.append(account_name)

        for account_name in expired:
            self.finished_accounts.discard(account_name)
            del self.account_finish_times[account_name]
            logger.info(f"[{self.profile_name}] Аккаунт {account_name} снова доступен (прошло 24 часа)")

    def _wait_for_threads(self):
        """Ждет завершения всех потоков"""
        logger.info(f"[{self.profile_name}] Ожидание завершения потоков...")

        while not self.stop_flag.is_set():
            alive = [t for t in self.chat_threads if t.is_alive()]

            if not alive:
                logger.info(f"[{self.profile_name}] Все потоки завершены")
                break

            # Проверяем условие остановки
            if self.user_queue.empty() and self.total_processed > 0:
                logger.info(f"[{self.profile_name}] Все пользователи обработаны")

            self.stop_flag.wait(10)

        # Ждем завершения потоков
        for thread in self.chat_threads:
            if thread.is_alive():
                thread.join(timeout=30)

    def update_account_stats(self, account_name: str, success: bool = False,
                             spam_block: bool = False, error: bool = False):
        """Обновляет статистику аккаунта и проверяет лимиты"""
        if account_name not in self.account_stats:
            self.account_stats[account_name] = AccountStats(name=account_name)

        stats = self.account_stats[account_name]

        if success:
            stats.invites += 1
            self.total_success += 1

            # Проверяем достиг ли аккаунт лимита
            if self.config.success_per_account > 0 and stats.invites >= self.config.success_per_account:
                stats.status = 'finished'
                self.finished_accounts.add(account_name)
                self.account_finish_times[account_name] = datetime.now()
                logger.warning(
                    f"[{self.profile_name}] Аккаунт {account_name} достиг лимита инвайтов: {stats.invites}")

                self._mark_account_as_finished(account_name)

        if error:
            stats.errors += 1
            self.total_errors += 1
        if spam_block:
            stats.spam_blocks += 1
            stats.consecutive_spam += 1

            if stats.spam_blocks >= self.config.acc_spam_limit:
                stats.status = 'spam_blocked'
                self.frozen_accounts.add(account_name)
                logger.error(f"[{self.profile_name}] Аккаунт {account_name} заблокирован за спам")
        else:
            stats.consecutive_spam = 0

        self.total_processed += 1

    def _mark_account_as_finished(self, account_name: str):
        """Помечает аккаунт как отработанный на 24 часа"""
        try:
            finish_time = datetime.now()
            self.account_finish_times[account_name] = finish_time
            next_available = finish_time + timedelta(hours=24)
            logger.info(f"📌 [{self.profile_name}] Аккаунт {account_name} помечен как отработанный")
            logger.info(f"   ⏰ Будет доступен: {next_available.strftime('%Y-%m-%d %H:%M:%S')}")
        except Exception as e:
            logger.error(f"❌ [{self.profile_name}] Ошибка пометки аккаунта {account_name}: {e}")

    def _print_final_stats(self):
        """Выводит финальную статистику"""
        logger.info("=" * 60)
        logger.info(f"[{self.profile_name}] 📊 ИТОГОВАЯ СТАТИСТИКА:")
        logger.info(f"[{self.profile_name}] Всего обработано: {self.total_processed}")
        logger.info(f"[{self.profile_name}] Успешных инвайтов: {self.total_success}")
        logger.info(f"[{self.profile_name}] Ошибок: {self.total_errors}")

        if self.total_processed > 0:
            success_rate = (self.total_success / self.total_processed) * 100
            logger.info(f"[{self.profile_name}] Процент успеха: {success_rate:.1f}%")

        # Статистика по правам админов
        if self.admin_rights_manager:
            rights_stats = self.admin_rights_manager.get_stats()
            logger.info(f"\n🤖 СТАТИСТИКА АДМИН-ПРАВ:")
            logger.info(f"   Чатов с правами: {rights_stats['total_chats_with_rights']}")
            logger.info(f"   Всего админов: {rights_stats['total_admins']}")
            logger.info(f"   Главных админов: {rights_stats['main_admins']}")
            logger.info(f"   Воркеров: {rights_stats['workers']}")

        logger.info("=" * 60)


class AdminChatWorkerThread(threading.Thread):
    """Рабочий поток для одного чата с управлением админ-правами через нового админа"""

    def __init__(self, chat_id: int, chat_link: str, main_admin_account: str,
                 worker_accounts: List[str], parent: AdminInviterProcess,
                 profile_name: str, bot_manager: BotManager,
                 admin_rights_manager: AdminRightsManager):
        super().__init__(name=f"AdminChat-{chat_id}")
        self.chat_id = chat_id
        self.chat_link = chat_link
        self.main_admin_account_name = main_admin_account
        self.worker_account_names = worker_accounts
        self.parent = parent
        self.profile_name = profile_name
        self.bot_manager = bot_manager
        self.admin_rights_manager = admin_rights_manager
        self.main_loop = None

        # Статистика чата
        self.chat_success = 0
        self.chat_errors = 0
        self.chat_processed = 0

        # Состояние главного админа
        self.main_admin_account = None
        self.main_admin_has_rights = False

        # ID чата для проверки общих чатов
        self.chat_telegram_id = None

    def run(self):
        """Основной метод потока"""
        try:
            # Создаем event loop для asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self.main_loop = loop

            # Запускаем работу
            loop.run_until_complete(self._work())

        except Exception as e:
            logger.error(f"❌ [{self.profile_name}]-[AdminChat-{self.chat_id}] Ошибка: {e}")
        finally:
            if loop:
                loop.close()

    async def _work(self):
        """Основная работа с чатом через админку"""
        logger.info(f"[{self.profile_name}]-[AdminChat-{self.chat_link}] 🤖 Начинаем работу через админку")

        try:
            # 1. Подготавливаем главного админа
            if not await self._setup_main_admin():
                logger.error(
                    f"[{self.profile_name}]-[AdminChat-{self.chat_link}] ❌ Не удалось настроить главного админа")
                return

            # 2. Работаем с воркерами последовательно
            await self._work_with_workers()

        except Exception as e:
            logger.error(f"[{self.profile_name}]-[AdminChat-{self.chat_link}] ❌ Ошибка в работе: {e}")
        finally:
            # 3. Финальная очистка - забираем права у главного админа
            await self._cleanup_main_admin()

        logger.info(f"[{self.profile_name}]-[AdminChat-{self.chat_link}] 🏁 Работа завершена")
        logger.info(
            f"   Статистика: обработано={self.chat_processed}, успешно={self.chat_success}, ошибок={self.chat_errors}")

    async def _setup_main_admin(self) -> bool:
        """Настраивает главного админа: заход в чат + получение прав от бота"""
        try:
            logger.info(
                f"[{self.profile_name}]-[AdminChat-{self.chat_link}] 👑 Настройка главного админа: {self.main_admin_account_name}")

            # Получаем аккаунт главного админа ИЗ ПАПКИ АДМИНЫ
            module_name = f"admin_inviter_{self.profile_name}"

            # Сначала пытаемся получить из обычного менеджера аккаунтов
            self.main_admin_account = self.parent.account_manager.get_account(
                self.main_admin_account_name, module_name
            )

            if not self.main_admin_account:
                # Если не нашли в обычном менеджере, создаем аккаунт из папки Админы
                logger.info(
                    f"[{self.profile_name}]-[AdminChat-{self.chat_link}] 🔍 Загружаем главного админа из папки Админы")
                self.main_admin_account = self._load_admin_from_folder()

            if not self.main_admin_account:
                logger.error(
                    f"[{self.profile_name}]-[AdminChat-{self.chat_link}] ❌ Не удалось получить аккаунт главного админа")
                return False

            # Подключаемся
            if not await self.main_admin_account.connect():
                logger.error(
                    f"[{self.profile_name}]-[AdminChat-{self.chat_link}] ❌ Не удалось подключиться к главному админу")
                return False

            # Заходим в чат
            join_result = await self._join_chat(self.main_admin_account, self.chat_link)
            if join_result == "FROZEN_ACCOUNT":
                logger.error(f"[{self.profile_name}]-[AdminChat-{self.chat_link}] ❌ Главный админ заморожен")
                return False
            elif join_result == "STOP_CHAT":
                logger.error(f"[{self.profile_name}]-[AdminChat-{self.chat_link}] ❌ Чат не найден")
                return False
            elif join_result != "SUCCESS":
                logger.warning(
                    f"[{self.profile_name}]-[AdminChat-{self.chat_link}] ⚠️ Главный админ не смог зайти в чат")
                return False

            # Получаем user_id главного админа и ID чата
            user_entity = await self.main_admin_account.client.get_entity('me')
            user_id = user_entity.id

            # Получаем entity чата для ID
            try:
                chat_entity = await self.main_admin_account.client.get_entity(self.chat_link)
                if hasattr(chat_entity, 'id'):
                    self.chat_telegram_id = chat_entity.id
                    logger.debug(
                        f"[{self.profile_name}]-[AdminChat-{self.chat_link}] Получен ID чата: {self.chat_telegram_id}")
            except Exception as e:
                logger.warning(f"[{self.profile_name}]-[AdminChat-{self.chat_link}] Не удалось получить ID чата: {e}")

            # Выдаем права через бота
            success = await self.admin_rights_manager.grant_main_admin_rights(
                self.chat_link, user_id, self.main_admin_account_name
            )

            if success:
                self.main_admin_has_rights = True
                logger.info(f"[{self.profile_name}]-[AdminChat-{self.chat_link}] ✅ Главный админ получил права")
                return True
            else:
                logger.error(
                    f"[{self.profile_name}]-[AdminChat-{self.chat_link}] ❌ Не удалось выдать права главному админу")
                return False

        except Exception as e:
            logger.error(f"[{self.profile_name}]-[AdminChat-{self.chat_link}] ❌ Ошибка настройки главного админа: {e}")
            return False

    def _load_admin_from_folder(self):
        """Загружает аккаунт главного админа из папки профиля/Админы"""
        try:
            profile_folder = Path(self.parent.profile_data['folder_path'])
            admins_folder = profile_folder / "Админы"

            # Ищем файлы аккаунта
            session_file = admins_folder / f"{self.main_admin_account_name}.session"
            json_file = admins_folder / f"{self.main_admin_account_name}.json"

            if not session_file.exists():
                logger.error(f"❌ Не найден session файл: {session_file}")
                return None

            if not json_file.exists():
                logger.error(f"❌ Не найден JSON файл: {json_file}")
                return None

            # Создаем аккаунт напрямую (минуя менеджер аккаунтов)
            from src.accounts.impl.account import Account
            account = Account(
                session_path=session_file,
                json_path=json_file
            )

            logger.info(f"✅ Загружен главный админ из папки Админы: {self.main_admin_account_name}")
            return account

        except Exception as e:
            logger.error(f"❌ Ошибка загрузки главного админа из папки: {e}")
            return None

    async def _work_with_workers(self):
        """Работает с воркерами последовательно: выдача прав -> инвайт -> отзыв прав"""
        module_name = f"admin_inviter_{self.profile_name}"

        for worker_name in self.worker_account_names:
            if self.parent.stop_flag.is_set():
                break

            try:
                logger.info(f"[{self.profile_name}]-[AdminChat-{self.chat_link}] 👷 Работаем с воркером: {worker_name}")

                # Получаем аккаунт воркера
                worker_account = self.parent.account_manager.get_account(worker_name, module_name)
                if not worker_account:
                    logger.error(
                        f"[{self.profile_name}]-[AdminChat-{self.chat_link}] ❌ Не удалось получить воркера: {worker_name}")
                    continue

                # Подключаемся к воркеру
                if not await worker_account.connect():
                    logger.error(
                        f"[{self.profile_name}]-[AdminChat-{self.chat_link}] ❌ Не удалось подключиться к воркеру: {worker_name}")
                    continue

                # Заходим в чат
                await self._join_chat(worker_account, self.chat_link)

                # Получаем user_id воркера
                user_entity = await worker_account.client.get_entity('me')
                user_id = user_entity.id

                # Выдаем права воркеру
                rights_granted = await self.admin_rights_manager.grant_worker_rights(
                    self.chat_link, user_id, worker_name
                )

                if rights_granted:
                    logger.info(
                        f"[{self.profile_name}]-[AdminChat-{self.chat_link}] ✅ Воркер {worker_name} получил права")

                    # Работаем с воркером
                    await self._work_with_worker_account(worker_account, worker_name)

                    # Забираем права у воркера
                    await self.admin_rights_manager.revoke_worker_rights(
                        self.chat_link, user_id, worker_name
                    )
                    logger.info(
                        f"[{self.profile_name}]-[AdminChat-{self.chat_link}] 🔒 Права отозваны у воркера: {worker_name}")
                else:
                    logger.error(
                        f"[{self.profile_name}]-[AdminChat-{self.chat_link}] ❌ Не удалось выдать права воркеру: {worker_name}")

            except Exception as e:
                logger.error(
                    f"[{self.profile_name}]-[AdminChat-{self.chat_link}] ❌ Ошибка работы с воркером {worker_name}: {e}")
            finally:
                # Освобождаем аккаунт
                self.parent.account_manager.release_account(worker_name, module_name)

    async def _work_with_worker_account(self, worker_account, worker_name: str):
        """Основной цикл инвайтинга для воркера"""
        invites_count = 0
        errors_count = 0

        while not self.parent.stop_flag.is_set():
            # Проверяем лимиты
            if self.parent.config.success_per_chat > 0 and self.chat_success >= self.parent.config.success_per_chat:
                logger.info(
                    f"[{self.profile_name}]-[AdminChat-{self.chat_link}] Достигнут лимит для чата: {self.chat_success}")
                break

            if self.parent.config.success_per_account > 0 and invites_count >= self.parent.config.success_per_account:
                logger.info(
                    f"[{self.profile_name}]-[AdminChat-{self.chat_link}] Достигнут лимит для аккаунта: {invites_count}")
                break

            # Получаем пользователя
            try:
                user = self.parent.user_queue.get_nowait()
            except queue.Empty:
                logger.info(f"[{self.profile_name}]-[AdminChat-{self.chat_link}] Очередь пользователей пуста")
                break

            # Инвайтим пользователя
            success = await self._invite_user(user, worker_account, worker_name)

            if success:
                invites_count += 1
                self.chat_success += 1
            else:
                errors_count += 1
                self.chat_errors += 1

            self.chat_processed += 1

            # Обновляем статистику
            self.parent.update_account_stats(
                worker_name,
                success=success,
                spam_block=(user.status == UserStatus.SPAM_BLOCK if hasattr(user, 'status') else False),
                error=(not success)
            )

            # Задержка между инвайтами
            if self.parent.config.delay_between > 0:
                await asyncio.sleep(self.parent.config.delay_between)

        logger.info(
            f"[{self.profile_name}]-[AdminChat-{self.chat_link}] Воркер {worker_name} завершен. Инвайтов: {invites_count}, ошибок: {errors_count}")

    async def _cleanup_main_admin(self):
        """Финальная очистка - забираем права у главного админа"""
        try:
            if self.main_admin_has_rights:
                logger.info(f"[{self.profile_name}]-[AdminChat-{self.chat_link}] 🧹 Забираем права у главного админа")

                await self.admin_rights_manager.revoke_main_admin_rights(self.chat_link)

                logger.info(f"[{self.profile_name}]-[AdminChat-{self.chat_link}] ✅ Права главного админа отозваны")
                self.main_admin_has_rights = False

            # Освобождаем главного админа
            if self.main_admin_account:
                module_name = f"admin_inviter_{self.profile_name}"
                self.parent.account_manager.release_account(self.main_admin_account_name, module_name)

        except Exception as e:
            logger.error(f"[{self.profile_name}]-[AdminChat-{self.chat_link}] ❌ Ошибка очистки главного админа: {e}")

    async def _join_chat(self, account, chat_link: str):
        """Заходит в чат"""
        try:
            from telethon.tl.functions.channels import JoinChannelRequest
            await account.client(JoinChannelRequest(chat_link))
            logger.info(f"[{self.profile_name}]-[AdminChat-{self.chat_link}] ✅ {account.name} зашел в чат")
            await asyncio.sleep(2)  # Небольшая задержка
        except Exception as e:
            logger.warning(
                f"[{self.profile_name}]-[AdminChat-{self.chat_link}] ⚠️ Ошибка захода в чат для {account.name}: {e}")

    async def _invite_user(self, user: InviteUser, account, account_name: str) -> bool:
        """Инвайт пользователя (логика из вашего кода)"""
        # Здесь используется ваша существующая логика _invite_user
        # Копируем из вашего кода без изменений
        client = account.client

        if not client or not client.is_connected():
            logger.error(f"❌ [{self.profile_name}]-[AdminChat-{self.chat_link}] Клиент не подключен")
            return False

        username = user.username
        if username.startswith('@'):
            username = username[1:]

        logger.info(
            f"[{self.profile_name}]-[AdminChat-{self.chat_link}] Пытаемся добавить @{username}")

        try:
            # Проверяем существование пользователя
            try:
                full_user = await client(GetFullUserRequest(username))
                old_common_chats = full_user.full_user.common_chats_count
            except (ValueError, TypeError, UsernameInvalidError, UsernameNotOccupiedError):
                logger.warning(
                    f"[{self.profile_name}]-[AdminChat-{self.chat_link}] Пользователь @{username} не существует")
                user.status = UserStatus.NOT_FOUND
                user.last_attempt = datetime.now()
                user.error_message = "Пользователь не найден"
                self.parent.processed_users[username] = user
                return False

            # Пытаемся пригласить
            try:
                user_entity = await client.get_entity(username)
                result = await client(InviteToChannelRequest(
                    channel=self.chat_link,
                    users=[user_entity]
                ))

                if hasattr(result, 'missing_invitees') and result.missing_invitees:
                    logger.warning(
                        f"[{self.profile_name}]-[AdminChat-{self.chat_link}] @{username} - настройки приватности")
                    user.status = UserStatus.PRIVACY
                    user.last_attempt = datetime.now()
                    user.error_message = "Настройки приватности"
                    self.parent.processed_users[username] = user
                    return False

            except UserPrivacyRestrictedError:
                logger.warning(
                    f"[{self.profile_name}]-[AdminChat-{self.chat_link}] @{username} - настройки приватности")
                user.status = UserStatus.PRIVACY
                user.last_attempt = datetime.now()
                user.error_message = "Настройки приватности"
                self.parent.processed_users[username] = user
                return False

            # Проверяем результат
            await asyncio.sleep(5)  # Меньше времени - у нас админ права

            full_user2 = await client(GetFullUserRequest(username))
            new_common_chats = full_user2.full_user.common_chats_count

            if new_common_chats <= old_common_chats:
                logger.warning(f"[{self.profile_name}]-[AdminChat-{self.chat_link}] @{username} списан")
                user.status = UserStatus.ERROR
                user.last_attempt = datetime.now()
                user.error_message = "Списание"
                self.parent.processed_users[username] = user
                return False

            # Успех
            logger.success(f"[{self.profile_name}]-[AdminChat-{self.chat_link}] @{username} успешно добавлен!")
            user.status = UserStatus.INVITED
            user.last_attempt = datetime.now()
            self.parent.processed_users[username] = user
            return True

        except (PeerFloodError, FloodWaitError) as e:
            if isinstance(e, FloodWaitError):
                wait_seconds = e.seconds
                logger.warning(f"[{self.profile_name}]-[AdminChat-{self.chat_link}] FloodWait: жду {wait_seconds} сек.")
                await asyncio.sleep(wait_seconds)
            else:
                logger.error(f"[{self.profile_name}]-[AdminChat-{self.chat_link}] Спамблок при добавлении @{username}")

            user.status = UserStatus.SPAM_BLOCK
            user.last_attempt = datetime.now()
            user.error_message = str(e)
            self.parent.processed_users[username] = user
            return False

        except Exception as e:
            logger.error(f"[{self.profile_name}]-[AdminChat-{self.chat_link}] Ошибка для @{username}: {e}")
            user.status = UserStatus.ERROR
            user.last_attempt = datetime.now()
            user.error_message = f"Ошибка: {str(e)[:50]}"
            self.parent.processed_users[username] = user
            return False