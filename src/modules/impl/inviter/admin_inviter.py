"""
Инвайтер через админку - использует бота для управления правами админов
ФИНАЛЬНАЯ ИСПРАВЛЕННАЯ ВЕРСИЯ с Threading и без двойного отключения
"""
import traceback
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
from .account_mover import AccountMover
from .utils import (
    get_fresh_accounts, clean_expired_accounts, load_main_admin_account,
    initialize_worker_clients, check_chat_limits, check_account_limits,
    mark_account_as_finished, print_final_stats, release_worker_accounts,
    determine_account_problem, safe_disconnect_account
)
from src.entities.moduls.inviter import InviteUser, UserStatus, AccountStats

# Импорты Telethon для ошибок
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
    """Инвайтер через админку с системой перемещения аккаунтов"""

    def __init__(self, profile_name: str, profile_data: Dict, account_manager):
        super().__init__(profile_name, profile_data, account_manager)

        profile_folder = Path(profile_data['folder_path'])
        from .data_loader import InviterDataLoader
        loader = InviterDataLoader(profile_folder)
        self.bot_token = loader._load_bot_token()

        # Главный админ аккаунт из конфигурации
        admins_folder = profile_folder / "Админы"
        self.main_admin_account_name = None

        if admins_folder.exists():
            session_files = list(admins_folder.glob("*.session"))
            if session_files:
                self.main_admin_account_name = session_files[0].stem
                logger.info(f"✅ Найден главный админ в папке Админы: {self.main_admin_account_name}")
            else:
                logger.error(f"❌ Нет .session файлов в папке Админы для {profile_name}")
        else:
            logger.error(f"❌ Папка Админы не существует для {profile_name}")

        if not self.main_admin_account_name:
            logger.error(f"❌ Не найден главный админ для {profile_name}")
            logger.error("💡 Переместите аккаунт в папку Админы через GUI")

        # Система перемещения аккаунтов
        self.account_mover = AccountMover(profile_folder)

        # Локальный список заблокированных аккаунтов для этого процесса
        self.blocked_accounts = set()

        # Менеджеры
        self.bot_manager: Optional[BotManager] = None
        self.admin_rights_manager: Optional[AdminRightsManager] = None

        # Потоки для чатов
        self.chat_threads = []

        # Статистика по аккаунтам
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

        self.main_loop = None

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
            # Сохраняем ссылку на текущий event loop
            self.main_loop = asyncio.get_event_loop()
            logger.debug(f"[{self.profile_name}] 🔄 Основной loop установлен: {id(self.main_loop)}")

            # 1. Инициализируем бот-менеджер
            if not await self._initialize_bot():
                logger.error(f"[{self.profile_name}] ❌ Не удалось инициализировать бота")
                return

            # 2. Взаимодействие с пользователем для настройки бота
            if not await self._user_interaction():
                logger.error(f"[{self.profile_name}] ❌ Настройка отменена пользователем")
                return

            # 3. Запускаем потоки для чатов
            await self._start_chat_threads()

        except Exception as e:
            logger.error(f"[{self.profile_name}] ❌ Ошибка в асинхронном процессе: {e}")
            logger.error(f"[{self.profile_name}] 🔍 Трассировка: {traceback.format_exc()}")
        finally:
            # Закрываем соединения
            if self.bot_manager:
                await self.bot_manager.disconnect()

    async def _initialize_bot(self) -> bool:
        """Инициализирует бот-менеджер"""
        try:
            logger.info(f"[{self.profile_name}] 🤖 Инициализация бота...")

            # Создаем бот-менеджер
            self.bot_manager = BotManager(
                bot_token=self.bot_token,
                proxy_url=None
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
        """Запускает потоки для чатов"""
        # Задержка после старта
        if self.config.delay_after_start > 0:
            logger.info(f"[{self.profile_name}] Задержка {self.config.delay_after_start} сек...")
            self.stop_flag.wait(self.config.delay_after_start)

        # Получаем начальное количество чатов
        total_chats = self.chat_queue.qsize()
        self.initial_chats_count = total_chats
        logger.info(f"[{self.profile_name}] Всего чатов для обработки: {total_chats}")

        # Рассчитываем требуемые аккаунты
        total_invites_needed = total_chats * self.config.success_per_chat if self.config.success_per_chat > 0 else 999999
        logger.info(f"[{self.profile_name}] Требуется успешных инвайтов всего: {total_invites_needed}")

        if self.config.success_per_account > 0:
            accounts_needed = (total_invites_needed + self.config.success_per_account - 1) // self.config.success_per_account
            logger.info(f"[{self.profile_name}] Расчетное количество аккаунтов: {accounts_needed}")
        else:
            accounts_needed = total_chats * self.config.threads_per_chat
            logger.info(f"[{self.profile_name}] Лимит на аккаунт не установлен, используем {accounts_needed} аккаунтов")

        # Проверяем доступность аккаунтов
        available_accounts = self.account_manager.get_free_accounts_count()
        logger.info(f"[{self.profile_name}] Доступно свободных аккаунтов: {available_accounts}")

        initial_accounts_to_request = min(accounts_needed, available_accounts,
                                          self.config.threads_per_chat * total_chats)

        if initial_accounts_to_request < accounts_needed:
            logger.warning(f"[{self.profile_name}] Недостаточно аккаунтов! Требуется: {accounts_needed}, доступно: {available_accounts}")

        # Загружаем главного админа
        if not self.main_admin_account_name:
            logger.error(f"[{self.profile_name}] ❌ Главный админ не настроен")
            return

        main_admin_account = load_main_admin_account(self)
        if not main_admin_account:
            logger.error(f"[{self.profile_name}] ❌ Не удалось загрузить главного админа")
            return

        logger.info(f"[{self.profile_name}] Главный админ загружен: {self.main_admin_account_name}")

        # Получаем воркеров
        module_name = f"admin_inviter_{self.profile_name}"
        allocated_worker_accounts = get_fresh_accounts(self, module_name, initial_accounts_to_request)

        if not allocated_worker_accounts:
            logger.error(f"[{self.profile_name}] Не удалось получить свободные воркер-аккаунты")
            return

        logger.info(f"[{self.profile_name}] Получено воркер-аккаунтов на старте: {len(allocated_worker_accounts)}")

        # Создаем потоки для чатов
        chat_index = 0
        worker_index = 0

        while self.chat_queue.qsize() > 0 and not self.stop_flag.is_set():
            try:
                chat = self.chat_queue.get_nowait()

                # Проверяем есть ли аккаунты для этого чата
                if worker_index >= len(allocated_worker_accounts):
                    # Пробуем получить еще аккаунты
                    additional_accounts = get_fresh_accounts(self, module_name, self.config.threads_per_chat)

                    if additional_accounts:
                        allocated_worker_accounts.extend(additional_accounts)
                        logger.info(f"[{self.profile_name}] Получено дополнительно {len(additional_accounts)} воркер-аккаунтов")
                    else:
                        # Возвращаем чат обратно в очередь
                        self.chat_queue.put(chat)
                        logger.warning(f"[{self.profile_name}] Нет воркеров для чата {chat}, отложен")
                        break

                # Выделяем воркеров для этого чата
                chat_worker_accounts = []
                workers_for_chat = min(self.config.threads_per_chat, len(allocated_worker_accounts) - worker_index)

                for j in range(workers_for_chat):
                    if worker_index < len(allocated_worker_accounts):
                        chat_worker_accounts.append(allocated_worker_accounts[worker_index])
                        worker_index += 1

                if not chat_worker_accounts:
                    # Возвращаем чат обратно
                    self.chat_queue.put(chat)
                    logger.warning(f"[{self.profile_name}] Не удалось выделить воркеров для чата {chat}")
                    break

                # Создаем поток для чата
                thread = AdminChatWorkerThread(
                    chat_id=chat_index + 1,
                    chat_link=chat,
                    main_admin_account=main_admin_account,
                    worker_accounts=chat_worker_accounts,
                    parent=self,
                    profile_name=self.profile_name,
                    bot_token=self.bot_token,
                    account_mover=self.account_mover
                )
                thread.start()
                self.chat_threads.append(thread)
                chat_index += 1

                logger.info(f"[{self.profile_name}] Запущен поток для чата #{chat_index}: {chat} (воркеров: {len(chat_worker_accounts)})")

            except queue.Empty:
                break

        # Ждем завершения всех потоков
        self._wait_for_threads()

        # Выводим итоговую статистику
        print_final_stats(self)

    def _wait_for_threads(self):
        """Ждет завершения всех потоков"""
        logger.info(f"[{self.profile_name}] Ожидание завершения потоков...")

        while not self.stop_flag.is_set():
            alive = [t for t in self.chat_threads if t.is_alive()]

            if not alive:
                logger.info(f"[{self.profile_name}] Все потоки завершены")
                break

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
                logger.warning(f"[{self.profile_name}] Аккаунт {account_name} достиг лимита инвайтов: {stats.invites}")

                # Помечаем как отработанный
                mark_account_as_finished(self, account_name)

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


class AdminChatWorkerThread(threading.Thread):
    """ИСПРАВЛЕННЫЙ рабочий поток для одного чата"""

    def __init__(self, chat_id: int, chat_link: str, main_admin_account,
                 worker_accounts: List, parent: AdminInviterProcess,
                 profile_name: str, bot_token: str, account_mover: AccountMover):
        super().__init__(name=f"AdminChat-{chat_id}")
        self.chat_id = chat_id
        self.chat_link = chat_link
        self.main_admin_account = main_admin_account
        self.main_admin_account_name = main_admin_account.name
        self.worker_accounts = worker_accounts
        self.parent = parent
        self.profile_name = profile_name
        self.bot_token = bot_token
        self.account_mover = account_mover

        # Локальные менеджеры
        self.bot_manager = None
        self.admin_rights_manager = None
        self.main_loop = None

        # Статистика чата
        self.chat_success = 0
        self.chat_errors = 0
        self.chat_processed = 0

        # Состояние
        self.main_admin_has_rights = False
        self.chat_telegram_id = None
        self.chat_stop_reason = None
        self.stop_all_workers = False

        # НОВОЕ: Для отслеживания отключенных аккаунтов
        self.disconnected_accounts = set()

    def run(self):
        """Основной метод потока"""
        try:
            # Создаем event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self.main_loop = loop

            # Запускаем работу
            loop.run_until_complete(self._work())

        except Exception as e:
            logger.error(f"❌ [{self.profile_name}]-[AdminChat-{self.chat_id}] Ошибка: {e}")
            logger.error(f"🔍 Трассировка: {traceback.format_exc()}")
        finally:
            if loop:
                loop.close()

    async def _work(self):
        """Основная работа с чатом"""
        logger.info(f"[{self.profile_name}]-[AdminChat-{self.chat_link}] 🤖 Начинаем работу через админку")
        logger.info(f"[{self.profile_name}]-[AdminChat-{self.chat_link}] Доступно воркеров: {len(self.worker_accounts)}")

        try:
            # 1. Создаем локальный bot manager
            if not await self._initialize_local_bot():
                logger.error(f"[{self.profile_name}]-[AdminChat-{self.chat_link}] ❌ Не удалось инициализировать локальный бот")
                return

            # 2. Подготавливаем главного админа
            if not await self._setup_main_admin():
                logger.error(f"[{self.profile_name}]-[AdminChat-{self.chat_link}] ❌ Не удалось настроить главного админа")
                return

            # 3. ИСПРАВЛЕНО: Работа с воркерами через отдельные потоки
            await self._work_with_workers_using_threads()

        except Exception as e:
            logger.error(f"[{self.profile_name}]-[AdminChat-{self.chat_link}] ❌ Ошибка в работе: {e}")
            logger.error(f"🔍 Трассировка: {traceback.format_exc()}")
        finally:
            # Финальная очистка
            await self._cleanup_main_admin()

            # Отключаем локальный бот
            if self.bot_manager:
                await self.bot_manager.disconnect()

        logger.info(f"[{self.profile_name}]-[AdminChat-{self.chat_link}] 🏁 Работа завершена")
        logger.info(f"   Статистика: обработано={self.chat_processed}, успешно={self.chat_success}, ошибок={self.chat_errors}")

    async def _work_with_workers_using_threads(self):
        """ИСПРАВЛЕННАЯ работа с воркерами через отдельные ПОТОКИ"""
        logger.info(f"[{self.profile_name}]-[AdminChat-{self.chat_link}] 🚀 Запуск воркеров через отдельные потоки")

        chat_completed = False
        module_name = f"admin_inviter_{self.parent.profile_name}"

        # Инициализируем клиенты ОДИН РАЗ
        await initialize_worker_clients(self.worker_accounts, self.parent)

        # Создаем список активных воркеров и блокировку
        active_worker_threads = []
        active_workers_lock = threading.Lock()
        active_workers_names = []

        # ГЛАВНЫЙ ЦИКЛ
        while not chat_completed and not self.parent.stop_flag.is_set():
            # Проверяем лимиты чата
            if not check_chat_limits(self.parent, self.chat_success):
                logger.info(f"[{self.profile_name}]-[AdminChat-{self.chat_link}] Достигнут лимит успешных инвайтов для чата: {self.chat_success}")
                chat_completed = True
                break

            if self.parent.user_queue.empty():
                logger.info(f"[{self.profile_name}]-[AdminChat-{self.chat_link}] Закончились пользователи для инвайта")
                chat_completed = True
                break

            # Запускаем воркеров в отдельных потоках
            replacement_needed = []

            for i, account_data in enumerate(self.worker_accounts):
                worker_name = account_data.name

                # Проверяем не проблемный ли аккаунт
                if (worker_name in self.parent.finished_accounts or
                        worker_name in self.parent.frozen_accounts or
                        worker_name in self.parent.blocked_accounts or
                        worker_name in self.disconnected_accounts):
                    replacement_needed.append(i)
                    continue

                # Проверяем не работает ли уже этот воркер
                with active_workers_lock:
                    if worker_name in active_workers_names:
                        continue

                # Создаем ОТДЕЛЬНЫЙ ПОТОК для воркера
                worker_thread = threading.Thread(
                    target=self._run_worker_in_thread,
                    args=(i + 1, account_data, active_workers_names, active_workers_lock),
                    name=f"Worker-{i+1}-{worker_name}"
                )
                worker_thread.start()
                active_worker_threads.append(worker_thread)

                logger.info(f"[{self.profile_name}]-[AdminChat-{self.chat_link}] 🚀 Запущен поток для воркера {worker_name}")

            # Ждем завершения воркеров (проверяем каждые 2 секунды)
            while active_worker_threads and not self.parent.stop_flag.is_set():
                if not check_chat_limits(self.parent, self.chat_success):
                    logger.info(f"[{self.profile_name}]-[AdminChat-{self.chat_link}] Достигнут лимит чата")
                    chat_completed = True
                    break

                if self.parent.user_queue.empty():
                    logger.info(f"[{self.profile_name}]-[AdminChat-{self.chat_link}] Пользователи закончились")
                    await asyncio.sleep(5)
                    chat_completed = True
                    break

                # Очищаем завершенные потоки
                active_worker_threads = [t for t in active_worker_threads if t.is_alive()]

                await asyncio.sleep(2)

            # Ждем завершения оставшихся потоков
            for thread in active_worker_threads:
                if thread.is_alive():
                    thread.join(timeout=10)

            # Получаем замещающие аккаунты если нужно
            if not chat_completed and replacement_needed:
                logger.info(f"[{self.profile_name}]-[AdminChat-{self.chat_link}] Получаем замещающие аккаунты...")

                replacement_accounts = get_fresh_accounts(self.parent, module_name, len(replacement_needed))

                if replacement_accounts:
                    # Заменяем проблемные аккаунты
                    for idx, new_account in zip(replacement_needed, replacement_accounts):
                        if idx < len(self.worker_accounts):
                            old_account = self.worker_accounts[idx]
                            logger.info(f"[{self.profile_name}]-[AdminChat-{self.chat_link}] Замена: {old_account.name} → {new_account.name}")
                            self.worker_accounts[idx] = new_account

                    # Инициализируем клиенты для новых аккаунтов
                    await initialize_worker_clients(replacement_accounts, self.parent)
                    replacement_needed.clear()
                else:
                    logger.warning(f"[{self.profile_name}]-[AdminChat-{self.chat_link}] Нет замещающих аккаунтов")
                    chat_completed = True

        logger.info(f"[{self.profile_name}]-[AdminChat-{self.chat_link}] Работа с воркерами завершена")

    def _run_worker_in_thread(self, worker_id: int, account_data, active_workers: list, lock: threading.Lock):
        """НОВАЯ ФУНКЦИЯ: Обертка для запуска воркера в отдельном потоке"""
        worker_name = account_data.name

        # Добавляем себя в список активных
        with lock:
            active_workers.append(worker_name)

        try:
            # Используем loop главного потока чата
            chat_loop = self.main_loop

            # Запускаем корутину в loop чата из отдельного потока
            future = asyncio.run_coroutine_threadsafe(
                self._run_worker_correctly(worker_id, account_data),
                chat_loop
            )

            # Ждем завершения
            future.result()

        except Exception as e:
            logger.error(f"[{self.profile_name}]-[Worker-{worker_id}] Ошибка в потоке: {e}")
        finally:
            # Удаляем себя из списка активных
            with lock:
                if worker_name in active_workers:
                    active_workers.remove(worker_name)

            logger.debug(f"[{self.profile_name}]-[Worker-{worker_id}]-[{worker_name}] 🏁 Поток воркера завершен")

    async def _run_worker_correctly(self, worker_id: int, account_data):
        """ИСПРАВЛЕННЫЙ воркер с защитой от двойного отключения"""

        worker_name = account_data.name
        worker_account = account_data.account
        is_disconnected = False  # ФЛАГ для защиты от двойного отключения

        logger.info(f"[{self.profile_name}]-[AdminChat-{self.chat_link}]-[Worker-{worker_id}] Запуск с воркером {worker_name}")

        try:
            # 1. ПОДКЛЮЧЕНИЕ К TELEGRAM
            if not worker_account.client:
                logger.error(f"[{self.profile_name}]-[Worker-{worker_id}]-[{worker_name}] Клиент не создан")
                return

            # ИСПРАВЛЕНО: Проверяем подключение БЕЗ повторного connect()
            if not worker_account.client.is_connected():
                if not await worker_account.connect():
                    logger.error(f"[{self.profile_name}]-[Worker-{worker_id}]-[{worker_name}] Не удалось подключить воркера")
                    return

            # Проверяем авторизацию
            if not await worker_account.client.is_user_authorized():
                logger.error(f"[{self.profile_name}]-[Worker-{worker_id}]-[{worker_name}] Воркер не авторизован")
                is_disconnected = True
                await worker_account.disconnect()
                self.disconnected_accounts.add(worker_name)
                return

            # Получаем информацию о воркере
            me = await worker_account.client.get_me()
            logger.info(f"[{self.profile_name}]-[Worker-{worker_id}]-[{worker_name}] Подключен как {me.first_name} {me.last_name or ''}")

            # 2. ВХОД В ЧАТ
            join_result = await self._join_chat(worker_account, self.chat_link)

            if join_result == "STOP_CHAT":
                logger.warning(f"[{self.profile_name}]-[Worker-{worker_id}]-[{worker_name}] Остановка всех воркеров чата")
                self.stop_all_workers = True
                is_disconnected = True
                await worker_account.disconnect()
                self.disconnected_accounts.add(worker_name)
                return
            elif join_result == "FROZEN_ACCOUNT":
                logger.error(f"[{self.profile_name}]-[Worker-{worker_id}]-[{worker_name}] Аккаунт заморожен")
                # ИСПРАВЛЕНО: Простая пометка как замороженного БЕЗ вызова handle_and_replace_account
                self.parent.frozen_accounts.add(worker_name)
                await self._handle_frozen_account_simple(worker_name)
                is_disconnected = True
                await worker_account.disconnect()
                self.disconnected_accounts.add(worker_name)
                return
            elif join_result != "SUCCESS":
                logger.error(f"[{self.profile_name}]-[Worker-{worker_id}]-[{worker_name}] Не удалось присоединиться к чату")
                is_disconnected = True
                await worker_account.disconnect()
                self.disconnected_accounts.add(worker_name)
                return

            # 3. ТЕПЕРЬ ВЫДАЕМ ПРАВА (после входа в чат!)
            user_entity = await worker_account.client.get_entity('me')
            worker_user_id = user_entity.id
            worker_user_access_hash = user_entity.access_hash

            # Получаем entity чата
            chat_entity = await self.main_admin_account.client.get_entity(self.chat_link)

            # ИСПРАВЛЕНО: Используем правильную функцию
            from .admin_rights_manager import grant_worker_rights_directly

            rights_granted = await grant_worker_rights_directly(
                main_admin_client=self.main_admin_account.client,
                chat_entity=chat_entity,
                worker_user_id=worker_user_id,
                worker_user_access_hash=worker_user_access_hash,
                worker_name=worker_name
            )

            if not rights_granted:
                logger.error(f"[{self.profile_name}]-[Worker-{worker_id}]-[{worker_name}] ❌ Не удалось выдать права воркеру")
                is_disconnected = True
                await worker_account.disconnect()
                self.disconnected_accounts.add(worker_name)
                return

            logger.info(f"[{self.profile_name}]-[Worker-{worker_id}]-[{worker_name}] ✅ Воркер получил права")

            # 4. ОСНОВНОЙ ЦИКЛ ИНВАЙТИНГА
            invites_count = 0
            errors_count = 0

            while not self.parent.stop_flag.is_set() and not self.stop_all_workers:
                # Проверяем лимиты аккаунта
                if not check_account_limits(self.parent, worker_name, invites_count):
                    logger.info(f"[{self.profile_name}]-[Worker-{worker_id}]-[{worker_name}] Воркер достиг лимита, завершаем работу")
                    break

                # Проверяем лимиты чата
                if not check_chat_limits(self.parent, self.chat_success):
                    logger.success(f"[{self.profile_name}]-[AdminChat-{self.chat_link}] Достигнут лимит успешных инвайтов: {self.chat_success}")
                    break

                # Получаем пользователя
                try:
                    user = self.parent.user_queue.get_nowait()
                except queue.Empty:
                    logger.info(f"[{self.profile_name}]-[Worker-{worker_id}] Очередь пуста")
                    break

                # Инвайтим пользователя
                try:
                    success = await self._invite_user(user, worker_account, worker_name, worker_id,
                                                      self.chat_link, self.chat_telegram_id)

                    if success:
                        invites_count += 1
                        self.chat_success += 1
                    else:
                        errors_count += 1

                    self.chat_processed += 1

                    # Обновляем статистику аккаунта
                    self.parent.update_account_stats(
                        worker_name,
                        success=success,
                        spam_block=(user.status == UserStatus.SPAM_BLOCK),
                        error=(not success)
                    )

                except (PeerFloodError, FloodWaitError, AuthKeyUnregisteredError, SessionRevokedError) as e:
                    # Критические ошибки - завершаем воркера
                    logger.error(f"[{self.profile_name}]-[Worker-{worker_id}]-[{worker_name}] Критическая ошибка: {e}")

                    # Помечаем пользователя
                    user.status = UserStatus.SPAM_BLOCK if 'flood' in str(e).lower() else UserStatus.ERROR
                    user.last_attempt = datetime.now()
                    user.error_message = str(e)
                    self.parent.processed_users[user.username] = user

                    # ИСПРАВЛЕНО: Простая пометка как проблемного БЕЗ замены
                    if 'flood' in str(e).lower():
                        self.parent.frozen_accounts.add(worker_name)
                        await self._handle_frozen_account_simple(worker_name)
                    else:
                        self.parent.blocked_accounts.add(worker_name)
                        await self._handle_blocked_account_simple(worker_name)

                    logger.warning(f"[{self.profile_name}]-[Worker-{worker_id}]-[{worker_name}] Воркер завершен из-за критической ошибки")
                    break

                except Exception as e:
                    # Обычные ошибки - просто логируем
                    logger.error(f"[{self.profile_name}]-[Worker-{worker_id}]-[{worker_name}] Ошибка инвайта: {e}")
                    errors_count += 1
                    self.chat_processed += 1

                    # Проверяем не критическая ли это ошибка
                    error_text = str(e).lower()
                    if any(keyword in error_text for keyword in ['unauthorized', 'session', 'auth_key']):
                        logger.error(f"[{self.profile_name}]-[Worker-{worker_id}]-[{worker_name}] Критическая ошибка аккаунта: {e}")
                        self.parent.blocked_accounts.add(worker_name)
                        await self._handle_blocked_account_simple(worker_name)
                        break

                # Задержка между инвайтами
                if self.parent.config.delay_between > 0:
                    await asyncio.sleep(self.parent.config.delay_between)

            # 5. ЗАБИРАЕМ ПРАВА У ВОРКЕРА (после завершения работы)
            try:
                # ИСПРАВЛЕНО: Используем правильную функцию
                from .admin_rights_manager import revoke_worker_rights_directly

                chat_entity = await self.main_admin_account.client.get_entity(self.chat_link)
                user_entity = await worker_account.client.get_entity('me')
                user_id = user_entity.id

                await revoke_worker_rights_directly(
                    main_admin_client=self.main_admin_account.client,
                    chat_entity=chat_entity,
                    worker_user_id=user_id,
                    worker_name=worker_name
                )
                logger.info(f"[{self.profile_name}]-[Worker-{worker_id}]-[{worker_name}] 🔒 Права воркера отозваны")
            except Exception as e:
                logger.error(f"[{self.profile_name}]-[Worker-{worker_id}]-[{worker_name}] ❌ Ошибка отзыва прав: {e}")

            logger.info(f"[{self.profile_name}]-[Worker-{worker_id}] Воркер завершен. Инвайтов: {invites_count}, ошибок: {errors_count}")

        except Exception as e:
            logger.error(f"[{self.profile_name}]-[Worker-{worker_id}] Критическая ошибка: {e}")
            # ИСПРАВЛЕНО: Простая пометка как заблокированного
            self.parent.blocked_accounts.add(worker_name)
            await self._handle_blocked_account_simple(worker_name)

        finally:
            # ИСПРАВЛЕНО: Отключаемся ТОЛЬКО ОДИН РАЗ
            if not is_disconnected and worker_name not in self.disconnected_accounts:
                try:
                    await worker_account.disconnect()
                    self.disconnected_accounts.add(worker_name)
                    logger.debug(f"[{self.profile_name}]-[Worker-{worker_id}]-[{worker_name}] 🔌 Воркер отключен")
                except Exception as e:
                    logger.warning(f"[{self.profile_name}]-[Worker-{worker_id}]-[{worker_name}] ⚠️ Ошибка отключения: {e}")

    async def _handle_frozen_account_simple(self, worker_name: str):
        """УПРОЩЕННАЯ обработка замороженного аккаунта БЕЗ двойного отключения"""
        try:
            logger.error(f"🧊 [{self.profile_name}] Замороженный аккаунт: {worker_name}")

            # Перемещаем файлы аккаунта
            success = self.parent.account_mover.move_account(worker_name, 'frozen')

            if success:
                logger.success(f"✅ [{self.profile_name}] Аккаунт {worker_name} перемещен в папку 'frozen'")
            else:
                logger.error(f"❌ [{self.profile_name}] Не удалось переместить аккаунт {worker_name}")

            # Освобождаем в менеджере
            module_name = f"admin_inviter_{self.parent.profile_name}"
            self.parent.account_manager.release_account(worker_name, module_name)
            logger.info(f"🔓 [{self.profile_name}] Аккаунт {worker_name} освобожден")

        except Exception as e:
            logger.error(f"❌ [{self.profile_name}] Ошибка обработки замороженного аккаунта {worker_name}: {e}")

    async def _handle_blocked_account_simple(self, worker_name: str):
        """УПРОЩЕННАЯ обработка заблокированного аккаунта БЕЗ двойного отключения"""
        try:
            logger.error(f"🚫 [{self.profile_name}] Заблокированный аккаунт: {worker_name}")

            # Перемещаем файлы аккаунта
            success = self.parent.account_mover.move_account(worker_name, 'dead')

            if success:
                logger.success(f"✅ [{self.profile_name}] Аккаунт {worker_name} перемещен в папку 'dead'")
            else:
                logger.error(f"❌ [{self.profile_name}] Не удалось переместить аккаунт {worker_name}")

            # Освобождаем в менеджере
            module_name = f"admin_inviter_{self.parent.profile_name}"
            self.parent.account_manager.release_account(worker_name, module_name)
            logger.info(f"🔓 [{self.profile_name}] Аккаунт {worker_name} освобожден")

        except Exception as e:
            logger.error(f"❌ [{self.profile_name}] Ошибка обработки заблокированного аккаунта {worker_name}: {e}")

    async def _initialize_local_bot(self) -> bool:
        """Инициализирует локальный bot manager для этого потока"""
        try:
            logger.info(f"[{self.profile_name}]-[AdminChat-{self.chat_link}] 🤖 Инициализация локального бота...")

            # Создаем свой bot manager
            self.bot_manager = BotManager(
                bot_token=self.bot_token,
                proxy_url=None
            )

            # Подключаемся
            if not await self.bot_manager.connect():
                logger.error(f"[{self.profile_name}]-[AdminChat-{self.chat_link}] ❌ Не удалось подключиться к локальному боту")
                return False

            # Создаем admin rights manager
            self.admin_rights_manager = AdminRightsManager(
                bot_manager=self.bot_manager
            )

            logger.info(f"[{self.profile_name}]-[AdminChat-{self.chat_link}] ✅ Локальный бот инициализирован: @{self.bot_manager.bot_username}")
            return True

        except Exception as e:
            logger.error(f"[{self.profile_name}]-[AdminChat-{self.chat_link}] ❌ Ошибка инициализации локального бота: {e}")
            return False

    async def _setup_main_admin(self) -> bool:
        """Настраивает главного админа: заход в чат + получение прав от бота"""
        try:
            logger.info(f"[{self.profile_name}]-[AdminChat-{self.chat_link}] 👑 Настройка главного админа: {self.main_admin_account_name}")

            # Создаем клиент если нужно
            if not self.main_admin_account.client:
                await self.main_admin_account.create_client()

            # Подключаемся
            if not await self.main_admin_account.connect():
                logger.error(f"[{self.profile_name}]-[AdminChat-{self.chat_link}] ❌ Не удалось подключиться к главному админу")
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
                logger.warning(f"[{self.profile_name}]-[AdminChat-{self.chat_link}] ⚠️ Главный админ не смог зайти в чат")
                return False

            # Получаем user_id главного админа
            user_entity = await self.main_admin_account.client.get_entity('me')
            user_id = user_entity.id

            # Получаем entity чата для ID
            try:
                chat_entity = await self.main_admin_account.client.get_entity(self.chat_link)
                if hasattr(chat_entity, 'id'):
                    self.chat_telegram_id = chat_entity.id
                    logger.debug(f"[{self.profile_name}]-[AdminChat-{self.chat_link}] Получен ID чата: {self.chat_telegram_id}")
            except Exception as e:
                logger.warning(f"[{self.profile_name}]-[AdminChat-{self.chat_link}] Не удалось получить ID чата: {e}")

            # Выдаем права главному админу
            logger.info(f"[{self.profile_name}]-[AdminChat-{self.chat_link}] 🔧 Выдача прав главному админу...")

            success = await self.admin_rights_manager.grant_main_admin_rights(
                self.chat_telegram_id, user_id, self.main_admin_account_name
            )

            if success:
                self.main_admin_has_rights = True
                logger.info(f"[{self.profile_name}]-[AdminChat-{self.chat_link}] ✅ Главный админ получил права")
                return True
            else:
                logger.error(f"[{self.profile_name}]-[AdminChat-{self.chat_link}] ❌ Не удалось выдать права главному админу")
                return False

        except Exception as e:
            logger.error(f"[{self.profile_name}]-[AdminChat-{self.chat_link}] ❌ Ошибка настройки главного админа: {e}")
            return False

    async def _cleanup_main_admin(self):
        """Финальная очистка - забираем права у главного админа"""
        try:
            if self.main_admin_has_rights and self.admin_rights_manager:
                logger.info(f"[{self.profile_name}]-[AdminChat-{self.chat_link}] 🧹 Забираем права у главного админа")

                await self.admin_rights_manager.revoke_main_admin_rights(self.chat_link)

                logger.info(f"[{self.profile_name}]-[AdminChat-{self.chat_link}] ✅ Права главного админа отозваны")
                self.main_admin_has_rights = False

            # Отключаем главного админа
            if self.main_admin_account and self.main_admin_account_name not in self.disconnected_accounts:
                await safe_disconnect_account(self.main_admin_account, self.main_admin_account_name)
                self.disconnected_accounts.add(self.main_admin_account_name)
                logger.info(f"[{self.profile_name}]-[AdminChat-{self.chat_link}] ✅ Главный админ отключен")

        except Exception as e:
            logger.error(f"[{self.profile_name}]-[AdminChat-{self.chat_link}] ❌ Ошибка очистки главного админа: {e}")

    async def _join_chat(self, account, chat_link: str):
        """Заходит в чат и возвращает результат"""
        try:
            result = await account.join(chat_link)

            if result == "ALREADY_PARTICIPANT":
                logger.info(f"[{self.profile_name}] Уже в чате {chat_link}")
                return "SUCCESS"

            elif result == "FROZEN_ACCOUNT":
                return "FROZEN_ACCOUNT"

            elif result == "CHAT_NOT_FOUND":
                logger.error(f"[{self.profile_name}] Чат не найден: {chat_link}")
                self.chat_stop_reason = "Чат не найден"
                return "STOP_CHAT"

            elif result == "REQUEST_SENT":
                logger.warning(f"[{self.profile_name}] Отправлен запрос на вступление в {chat_link}")
                return False

            elif result == "FLOOD_WAIT":
                logger.warning(f"[{self.profile_name}] Нужно подождать перед присоединением в {chat_link}")
                return False

            elif isinstance(result, str) and result.startswith("ERROR:"):
                logger.error(f"❌ [{self.profile_name}] Ошибка: {result}")
                return False
            else:
                # Успешно присоединились
                logger.info(f"[{self.profile_name}] {account.name} присоединился к чату {chat_link}")

                # Сохраняем информацию о чате
                if hasattr(result, 'id'):
                    self.chat_telegram_id = result.id

                # Задержка после присоединения
                if self.parent.config.delay_after_start > 0:
                    await asyncio.sleep(self.parent.config.delay_after_start)

                return "SUCCESS"

        except Exception as e:
            logger.error(f"[{self.profile_name}] Ошибка присоединения к чату {chat_link}: {e}")
            return False

    async def _invite_user(self, user: InviteUser, account, account_name: str, worker_id: int,
                           chat_link: str, chat_telegram_id: Optional[int]) -> bool:
        """Инвайт пользователя через Telethon"""
        client = account.client

        if not client or not client.is_connected():
            logger.error(f"❌ [{self.profile_name}]-[Worker-{worker_id}]-[{account_name}] Клиент не подключен")
            return False

        username = user.username
        if username.startswith('@'):
            username = username[1:]

        logger.info(f"[{self.profile_name}]-[Worker-{worker_id}]-[{account_name}] Пытаемся добавить @{username} в {chat_link}")

        try:
            # 1. Проверяем существование пользователя и получаем количество общих чатов
            try:
                full_user = await client(GetFullUserRequest(username))
                old_common_chats = full_user.full_user.common_chats_count
            except (ValueError, TypeError, UsernameInvalidError, UsernameNotOccupiedError):
                logger.warning(f"[{self.profile_name}]-[Worker-{worker_id}]-[{account_name}] Пользователь @{username} не существует")
                user.status = UserStatus.NOT_FOUND
                user.last_attempt = datetime.now()
                user.error_message = "Пользователь не найден"
                self.parent.processed_users[username] = user
                return False

            # 1.5 Проверяем общие чаты если есть ID текущего чата
            if chat_telegram_id and old_common_chats > 0:
                try:
                    # Получаем user entity
                    user_entity = await client.get_entity(username)

                    # Запрашиваем общие чаты
                    common_chats_result = await client(GetCommonChatsRequest(
                        user_id=user_entity,
                        max_id=0,
                        limit=100
                    ))

                    # Проверяем есть ли среди них наш чат
                    for chat in common_chats_result.chats:
                        if hasattr(chat, 'id') and chat.id == chat_telegram_id:
                            logger.warning(f"👥 [{self.profile_name}]-[Worker-{worker_id}]-[{account_name}] @{username} уже в чате! (Чат: {chat_link})")
                            user.status = UserStatus.ALREADY_IN
                            user.last_attempt = datetime.now()
                            user.error_message = "Уже в чате"
                            self.parent.processed_users[username] = user
                            return False

                    logger.debug(f"[{self.profile_name}]-[Worker-{worker_id}]-[{account_name}] @{username} не найден в текущем чате (Чат: {chat_link})")

                except Exception as e:
                    # Если не удалось проверить - продолжаем инвайт
                    logger.debug(f"⚠[{self.profile_name}]-[Worker-{worker_id}]-[{account_name}] Не удалось проверить общие чаты: {e}")

            # 2. Пытаемся пригласить
            result = await client(InviteToChannelRequest(
                channel=chat_link,
                users=[username]
            ))

            # Проверяем есть ли missing_invitees (приватность)
            if result.missing_invitees:
                logger.warning(f"[{self.profile_name}]-[Worker-{worker_id}]-[{account_name}] @{username} - настройки приватности (Чат: {chat_link})")
                user.status = UserStatus.PRIVACY
                user.last_attempt = datetime.now()
                user.error_message = "Настройки приватности"
                self.parent.processed_users[username] = user
                return False

            # 3. Ждем и проверяем действительно ли добавился
            await asyncio.sleep(20)  # Даем время на обработку

            full_user2 = await client(GetFullUserRequest(username))
            new_common_chats = full_user2.full_user.common_chats_count

            # Если количество общих чатов не увеличилось - списание
            if new_common_chats <= old_common_chats:
                logger.warning(f"[{self.profile_name}]-[Worker-{worker_id}]-[{account_name}] @{username} добавлен и сразу списан (Чат: {chat_link})")
                user.status = UserStatus.ERROR
                user.last_attempt = datetime.now()
                user.error_message = "Списание"
                self.parent.processed_users[username] = user
                return False

            # Успешно добавлен
            logger.success(f"[{self.profile_name}]-[Worker-{worker_id}]-[{account_name}] @{username} успешно добавлен! (Чат: {chat_link})")
            user.status = UserStatus.INVITED
            user.last_attempt = datetime.now()
            self.parent.processed_users[username] = user
            return True

        except (PeerFloodError, FloodWaitError) as e:
            if isinstance(e, FloodWaitError):
                wait_seconds = e.seconds
                logger.warning(f"[{self.profile_name}]-[Worker-{worker_id}]-[{account_name}] @{username} FloodWait: жду {wait_seconds} сек.")
                await asyncio.sleep(wait_seconds)
            else:
                logger.error(f"[{self.profile_name}]-[Worker-{worker_id}]-[{account_name}] @{username} Спамблок при добавлении")

            user.status = UserStatus.SPAM_BLOCK
            user.last_attempt = datetime.now()
            user.error_message = str(e)
            self.parent.processed_users[username] = user
            return False

        except UserPrivacyRestrictedError:
            logger.warning(f"[{self.profile_name}]-[Worker-{worker_id}]-[{account_name}] @{username} - настройки приватности (Чат: {chat_link})")
            user.status = UserStatus.PRIVACY
            user.last_attempt = datetime.now()
            user.error_message = "Настройки приватности"
            self.parent.processed_users[username] = user
            return False

        except (UserDeactivatedBanError, UserDeactivatedError):
            logger.warning(f"[{self.profile_name}]-[Worker-{worker_id}]-[{account_name}] @{username} заблокирован в Telegram (Чат: {chat_link})")
            user.status = UserStatus.NOT_FOUND
            user.last_attempt = datetime.now()
            user.error_message = "Пользователь заблокирован"
            self.parent.processed_users[username] = user
            return False

        except (ChatAdminRequiredError, ChatWriteForbiddenError):
            logger.error(f"[{self.profile_name}]-[Worker-{worker_id}]-[{account_name}] Недостаточно прав в чате (Чат: {chat_link})")
            user.status = UserStatus.ERROR
            user.last_attempt = datetime.now()
            user.error_message = "Недостаточно прав в чате"
            self.parent.processed_users[username] = user
            return False

        except ChannelsTooMuchError:
            logger.warning(f"[{self.profile_name}]-[Worker-{worker_id}]-[{account_name}] @{username} уже в максимальном количестве чатов (Чат: {chat_link})")
            user.status = UserStatus.ERROR
            user.last_attempt = datetime.now()
            user.error_message = "Максимум чатов"
            self.parent.processed_users[username] = user
            return False

        except Exception as e:
            # Специфичные ошибки по тексту
            error_text = str(e)

            if "CHAT_MEMBER_ADD_FAILED" in error_text:
                logger.error(f"[{self.profile_name}]-[Worker-{worker_id}]-[{account_name}] Не удалось добавить @{username} (Чат: {chat_link})")
                user.status = UserStatus.ERROR
                user.error_message = "Ошибка добавления"

            elif "You're banned from sending messages" in error_text:
                logger.error(f"[{self.profile_name}]-[Worker-{worker_id}]-[{account_name}] Аккаунт заблокирован для инвайтов (Чат: {chat_link})")
                user.status = UserStatus.ERROR
                user.error_message = "Аккаунт заблокирован"

            elif "user was kicked" in error_text.lower():
                logger.warning(f"[{self.profile_name}]-[Worker-{worker_id}]-[{account_name}] @{username} был ранее кикнут из чата (Чат: {chat_link})")
                user.status = UserStatus.ALREADY_IN
                user.error_message = "Был кикнут"

            elif "already in too many channels" in error_text.lower():
                logger.warning(f"[{self.profile_name}]-[Worker-{worker_id}]-[{account_name}] @{username} в слишком многих чатах (Чат: {chat_link})")
                user.status = UserStatus.ERROR
                user.error_message = "Слишком много чатов"

            else:
                logger.error(f"[{self.profile_name}]-[Worker-{worker_id}]-[{account_name}] Неизвестная ошибка для @{username}: {e} (Чат: {chat_link})")
                user.status = UserStatus.ERROR
                user.error_message = f"Ошибка: {error_text[:50]}"

            user.last_attempt = datetime.now()
            self.parent.processed_users[username] = user
            return False