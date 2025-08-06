# src/modules/impl/inviter/admin_inviter.py - ПОЛНОСТЬЮ ИСПРАВЛЕННЫЙ
"""
ИСПРАВЛЕНО: Админ-инвайтер с автоматической сменой аккаунтов и отдельными админами для каждого чата
"""
import traceback
import threading
import asyncio
import queue
import time
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from loguru import logger
from pathlib import Path
from dataclasses import dataclass

from .base_inviter import BaseInviterProcess
from .bot_manager import BotManager
from .admin_rights_manager import AdminRightsManager
from .account_mover import AccountMover
from .utils import (
    clean_expired_accounts, check_chat_limits,
    check_account_limits, mark_account_as_finished, print_final_stats,
    ensure_main_admin_ready_in_chat
)
from src.entities.moduls.inviter import InviteUser, UserStatus, AccountStats

# Импорты Telethon
from telethon.tl.functions.channels import InviteToChannelRequest
from telethon.tl.functions.users import GetFullUserRequest
from telethon.tl.functions.messages import GetCommonChatsRequest
from telethon.errors import (
    UsernameInvalidError, UsernameNotOccupiedError, PeerFloodError, FloodWaitError,
    UserPrivacyRestrictedError, ChatAdminRequiredError, ChatWriteForbiddenError,
    UserDeactivatedBanError, UserDeactivatedError, AuthKeyUnregisteredError, SessionRevokedError
)


@dataclass
class AdminCommand:
    """Команда для главного админа"""
    action: str  # "GRANT_RIGHTS" или "REVOKE_RIGHTS"
    worker_name: str
    worker_user_id: int
    worker_access_hash: int
    chat_link: str
    response_queue: queue.Queue  # Для ответа воркеру


@dataclass
class AccountErrorCounters:
    """Счетчики ошибок для аккаунта"""
    consecutive_spam_blocks: int = 0
    consecutive_writeoffs: int = 0
    consecutive_block_invites: int = 0

    def reset_all(self):
        """Сброс всех счетчиков"""
        self.consecutive_spam_blocks = 0
        self.consecutive_writeoffs = 0
        self.consecutive_block_invites = 0

    def reset_spam_blocks(self):
        """Сброс счетчика спам-блоков"""
        self.consecutive_spam_blocks = 0

    def reset_writeoffs(self):
        """Сброс счетчика списаний"""
        self.consecutive_writeoffs = 0

    def reset_block_invites(self):
        """Сброс счетчика блоков инвайтов"""
        self.consecutive_block_invites = 0


@dataclass
class ChatAdmin:
    """Информация о главном админе чата"""
    name: str
    account: Optional[object] = None
    session_path: Optional[Path] = None
    json_path: Optional[Path] = None
    is_ready: bool = False


class AdminInviterProcess(BaseInviterProcess):
    """Инвайтер с фоновой системой команд для главного админа + сохранение прогресса"""

    def __init__(self, profile_name: str, profile_data: Dict, account_manager):
        super().__init__(profile_name, profile_data, account_manager)

        profile_folder = Path(profile_data['folder_path'])
        from .data_loader import InviterDataLoader
        loader = InviterDataLoader(profile_folder)
        self.bot_token = loader._load_bot_token()

        # НОВОЕ: Главные админы для каждого чата
        admins_folder = profile_folder / "Админы"
        self.available_admins = []
        self.chat_admins: Dict[str, ChatAdmin] = {}  # {chat_link: ChatAdmin}

        if admins_folder.exists():
            session_files = list(admins_folder.glob("*.session"))
            for session_file in session_files:
                admin_name = session_file.stem
                json_file = admins_folder / f"{admin_name}.json"
                if json_file.exists():
                    self.available_admins.append(admin_name)
                    logger.success(f"[{self.profile_name}] Найден админ: {admin_name}")

        logger.info(f"[{self.profile_name}] Всего доступных админов: {len(self.available_admins)}")

        # Система перемещения
        self.account_mover = AccountMover(profile_folder)

        # Менеджеры
        self.bot_manager: Optional[BotManager] = None
        self.admin_rights_manager: Optional[AdminRightsManager] = None

        # Очереди для команд
        self.admin_command_queue = queue.Queue()
        self.admin_stop_event = threading.Event()

        # Потоки
        self.chat_threads = []

        # Список готовых чатов
        self.ready_chats = set()

        # Статистика
        self.account_stats: Dict[str, AccountStats] = {}
        self.total_success = 0
        self.total_errors = 0
        self.total_processed = 0
        self.frozen_accounts = set()
        self.finished_accounts = set()
        self.blocked_accounts = set()
        self.account_finish_times: Dict[str, datetime] = {}

        # Статистика по чатам для отчета
        self.chat_stats: Dict[str, Dict] = {}  # {chat_link: {"success": 0, "total": 0}}

        # Счетчики ошибок для каждого аккаунта
        self.account_error_counters: Dict[str, AccountErrorCounters] = {}

        # Специфичные типы проблем для правильного перемещения
        self.writeoff_accounts = set()  # Списанные
        self.spam_block_accounts = set()  # Спам-блок
        self.block_invite_accounts = set()  # Блок инвайтов
        self.finished_successfully_accounts = set()  # Успешно отработанные

        # Множество обработанных аккаунтов для предотвращения повторного использования
        self.processed_accounts = set()

        # Флаг для отслеживания уведомления о нехватке аккаунтов
        self.no_accounts_notified = False

        # Блокировка для thread-safe записи в файл
        self.file_write_lock = threading.Lock()

        # Путь к файлу пользователей для сохранения прогресса
        self.users_file_path = profile_folder / "База юзеров.txt"

    def get_fresh_accounts(self, module_name: str, count: int) -> List:
        """
        Получение свежих аккаунтов с проверкой уже обработанных
        """
        try:
            # Получаем аккаунты из менеджера
            accounts = self.account_manager.get_free_accounts(module_name, count)

            if not accounts:
                logger.warning(f"[{self.profile_name}] Менеджер не предоставил аккаунты (запрошено: {count})")
                return []

            # Фильтруем уже обработанные аккаунты
            fresh_accounts = []
            for account_data in accounts:
                if account_data.name not in self.processed_accounts:
                    fresh_accounts.append(account_data)
                else:
                    # Освобождаем аккаунт обратно, так как он уже был обработан
                    try:
                        self.account_manager.release_account(account_data.name, module_name)
                    except Exception as e:
                        logger.error(
                            f"[{self.profile_name}] Ошибка освобождения обработанного аккаунта {account_data.name}: {e}")

            if fresh_accounts:
                logger.success(f"[{self.profile_name}] Получено свежих аккаунтов: {len(fresh_accounts)}")
            else:
                logger.warning(f"[{self.profile_name}] Все полученные аккаунты уже были обработаны")

            return fresh_accounts

        except Exception as e:
            logger.error(f"[{self.profile_name}] Ошибка получения аккаунтов от менеджера: {e}")
            return []

    def check_accounts_availability(self) -> bool:
        """
        Проверяет есть ли доступные неиспользованные аккаунты у менеджера
        """
        try:
            free_count = self.account_manager.get_free_accounts_count()

            # Учитываем уже обработанные аккаунты
            estimated_available = max(0, free_count - len(self.processed_accounts))

            return estimated_available > 0
        except Exception as e:
            logger.error(f"[{self.profile_name}] Ошибка проверки доступности аккаунтов: {e}")
            return False

    def _get_account_error_counters(self, account_name: str) -> AccountErrorCounters:
        """Получение счетчиков ошибок для аккаунта"""
        if account_name not in self.account_error_counters:
            self.account_error_counters[account_name] = AccountErrorCounters()
        return self.account_error_counters[account_name]

    def _check_account_error_limits(self, account_name: str, error_type: str) -> bool:
        """
        Проверка лимитов ошибок для аккаунта
        Возвращает True если аккаунт нужно завершить, False если можно продолжать
        """
        counters = self._get_account_error_counters(account_name)

        if error_type == "spam_block":
            counters.consecutive_spam_blocks += 1
            counters.reset_writeoffs()
            counters.reset_block_invites()

            if counters.consecutive_spam_blocks >= self.config.acc_spam_limit:
                logger.error(
                    f"[{self.profile_name}] Аккаунт {account_name} превысил лимит спам-блоков: {counters.consecutive_spam_blocks}/{self.config.acc_spam_limit}")
                return True

        elif error_type == "writeoff":
            counters.consecutive_writeoffs += 1
            counters.reset_spam_blocks()
            counters.reset_block_invites()

            if counters.consecutive_writeoffs >= self.config.acc_writeoff_limit:
                logger.error(
                    f"[{self.profile_name}] Аккаунт {account_name} превысил лимит списаний: {counters.consecutive_writeoffs}/{self.config.acc_writeoff_limit}")
                return True

        elif error_type == "block_invite":
            counters.consecutive_block_invites += 1
            counters.reset_spam_blocks()
            counters.reset_writeoffs()

            if counters.consecutive_block_invites >= self.config.acc_block_invite_limit:
                logger.error(
                    f"[{self.profile_name}] Аккаунт {account_name} превысил лимит блоков инвайтов: {counters.consecutive_block_invites}/{self.config.acc_block_invite_limit}")
                return True

        elif error_type == "success":
            # При успехе сбрасываем все счетчики
            counters.reset_all()

        return False

    def _mark_account_as_processed(self, account_name: str, reason: str):
        """
        Помечает аккаунт как обработанный чтобы он больше не использовался
        """
        self.processed_accounts.add(account_name)
        logger.debug(f"[{self.profile_name}] Аккаунт {account_name} помечен как обработанный: {reason}")

    def _update_account_status_in_manager_sync(self, account_name: str, new_status: str):
        """
        Синхронное обновление статуса в менеджере
        """
        try:
            if hasattr(self.account_manager, 'traffic_accounts'):
                if account_name in self.account_manager.traffic_accounts:
                    account_data = self.account_manager.traffic_accounts[account_name]

                    old_status = account_data.status
                    account_data.status = new_status
                    account_data.is_busy = False
                    account_data.busy_by = None

                else:
                    logger.warning(
                        f"[{self.profile_name}] Аккаунт {account_name} не найден в traffic_accounts менеджера")
            else:
                logger.warning(f"[{self.profile_name}] У менеджера нет traffic_accounts")
        except Exception as e:
            logger.error(f"[{self.profile_name}] КРИТИЧЕСКАЯ ошибка обновления статуса в менеджере: {e}")

    def _save_users_progress_to_file(self):
        """
        Сохраняет прогресс пользователей в файл (thread-safe) БЕЗ БЭКАПОВ
        """
        try:
            with self.file_write_lock:  # Thread-safe запись
                logger.info(f"💾 [{self.profile_name}] Сохранение прогресса пользователей в файл...")

                # Собираем всех пользователей в правильном формате
                all_lines = []

                # 1. Сначала добавляем всех обработанных пользователей
                for username, user in self.processed_users.items():
                    line = self._format_user_for_file(user)
                    if line:
                        all_lines.append(line)

                # 2. Затем добавляем оставшихся необработанных пользователей из очереди
                remaining_users = []
                try:
                    while not self.user_queue.empty():
                        user = self.user_queue.get_nowait()
                        remaining_users.append(user)
                        # Добавляем чистого пользователя
                        all_lines.append(f"@{user.username}")
                except queue.Empty:
                    pass

                # Возвращаем пользователей обратно в очередь
                for user in remaining_users:
                    self.user_queue.put(user)

                # 3. Записываем прямо в основной файл БЕЗ БЭКАПА
                content = '\n'.join(all_lines)
                self.users_file_path.write_text(content, encoding='utf-8', errors='replace')

                logger.success(f"💾 [{self.profile_name}] Прогресс сохранен в основной файл: {len(all_lines)} записей")
                logger.info(f"   📊 Обработанных: {len(self.processed_users)}")
                logger.info(f"   📊 Оставшихся: {len(remaining_users)}")

        except Exception as e:
            logger.error(f"❌ [{self.profile_name}] КРИТИЧЕСКАЯ ошибка сохранения прогресса: {e}")
            logger.error(f"❌ [{self.profile_name}] Стек ошибки:\n{traceback.format_exc()}")

    def _format_user_for_file(self, user: InviteUser) -> str:
        """
        Форматирует пользователя для записи в файл
        """
        try:
            username = user.username
            if not username.startswith('@'):
                username = f"@{username}"

            # Формируем статус и сообщение
            if user.status == UserStatus.INVITED:
                status_text = "✅ Приглашен"
            elif user.status == UserStatus.PRIVACY:
                status_text = "🔒 Настройки приватности"
            elif user.status == UserStatus.ALREADY_IN:
                status_text = "👥 Уже в чате"
            elif user.status == UserStatus.SPAM_BLOCK:
                status_text = "🚫 Спамблок"
            elif user.status == UserStatus.NOT_FOUND:
                status_text = "❓ Не найден"
            elif user.status == UserStatus.ERROR:
                status_text = f"❌ Ошибка: {user.error_message or 'Неизвестная'}"
            else:
                # Для чистых пользователей возвращаем просто username
                return username

            # Добавляем детали если есть
            if user.error_message and user.error_message != status_text:
                status_text += f" - {user.error_message}"

            return f"{username}: {status_text}"

        except Exception as e:
            logger.error(f"❌ Ошибка форматирования пользователя {user.username}: {e}")
            return f"@{user.username}: ❌ Ошибка форматирования"

    def _assign_admins_to_chats(self):
        """
        НОВОЕ: Назначает отдельного админа каждому чату
        """
        # Получаем все чаты
        chat_links = []
        temp_chats = []
        while not self.chat_queue.empty():
            chat = self.chat_queue.get_nowait()
            chat_links.append(chat)
            temp_chats.append(chat)
        for chat in temp_chats:
            self.chat_queue.put(chat)

        if not chat_links:
            logger.error(f"[{self.profile_name}] Нет чатов для назначения админов")
            return False

        if len(self.available_admins) < len(chat_links):
            logger.error(
                f"[{self.profile_name}] Недостаточно админов: {len(self.available_admins)} админов для {len(chat_links)} чатов")
            return False

        # Назначаем админа каждому чату
        profile_folder = Path(self.profile_data['folder_path'])
        admins_folder = profile_folder / "Админы"

        for i, chat_link in enumerate(chat_links):
            admin_name = self.available_admins[i]

            chat_admin = ChatAdmin(
                name=admin_name,
                session_path=admins_folder / f"{admin_name}.session",
                json_path=admins_folder / f"{admin_name}.json"
            )

            self.chat_admins[chat_link] = chat_admin
            logger.success(f"[{self.profile_name}] Чат {chat_link} -> Админ {admin_name}")

        return True

    def _run_inviting(self):
        """Основная логика с добавлением сохранения прогресса"""
        logger.success(f"[{self.profile_name}] Запуск админ-инвайтинга")

        if not self.bot_token or not self.available_admins:
            logger.error(f"[{self.profile_name}] Не настроен бот или нет админов")
            return

        # Инициализация статусов пользователей из файла
        self._load_user_statuses()

        try:
            asyncio.run(self._async_run_inviting())
        except Exception as e:
            logger.error(f"[{self.profile_name}] Критическая ошибка: {e}")
        finally:
            self.is_running = False
            self.finished_at = datetime.now()

            # Сохраняем прогресс пользователей
            logger.info(f"💾 [{self.profile_name}] Финальное сохранение прогресса...")
            self._save_users_progress_to_file()

            # Сохраняем отчет и статусы пользователей
            self._save_user_statuses()
            self._generate_final_report()

    async def _async_run_inviting(self):
        """Асинхронная логика"""
        try:
            # 1. Инициализация бота
            if not await self._init_bot():
                return

            # 2. Настройка бота пользователем
            if not await self._setup_bot():
                return

            # 3. НОВОЕ: Назначение админов чатам
            if not self._assign_admins_to_chats():
                return

            # 4. Создание и подключение админов для каждого чата
            if not await self._setup_chat_admins():
                return

            # 5. Подготовка админов во всех чатах
            if not await self._prepare_admins_in_chats():
                return

            # 6. ГЛАВНОЕ: Запуск основного цикла работы
            await self._main_work_loop()

        except Exception as e:
            logger.error(f"[{self.profile_name}] Ошибка: {e}")
        finally:
            await self._cleanup()

    async def _init_bot(self) -> bool:
        """Инициализация бота"""
        try:
            self.bot_manager = BotManager(bot_token=self.bot_token, proxy_url=None)

            if not await self.bot_manager.connect():
                return False

            self.admin_rights_manager = AdminRightsManager(bot_manager=self.bot_manager)
            logger.success(f"[{self.profile_name}] Бот готов: @{self.bot_manager.bot_username}")
            return True
        except Exception as e:
            logger.error(f"[{self.profile_name}] Ошибка бота: {e}")
            return False

    async def _setup_bot(self) -> bool:
        """Настройка бота пользователем"""
        # Получаем чаты
        chat_links = []
        temp_chats = []
        while not self.chat_queue.empty():
            chat = self.chat_queue.get_nowait()
            chat_links.append(chat)
            temp_chats.append(chat)
        for chat in temp_chats:
            self.chat_queue.put(chat)

        if not chat_links:
            return False

        # Проверка
        setup_needed = []
        for chat in chat_links:
            is_admin = await self.bot_manager.check_bot_admin_status(chat)
            if not is_admin:
                setup_needed.append(chat)
                logger.warning(f"[{self.profile_name}] Требует настройки: {chat}")
            else:
                logger.success(f"[{self.profile_name}] Бот готов в чате: {chat}")

        if setup_needed:
            await asyncio.sleep(60)

        return True

    async def _setup_chat_admins(self) -> bool:
        """
        НОВОЕ: Создание и подключение админов для каждого чата
        """
        try:
            for chat_link, chat_admin in self.chat_admins.items():
                logger.info(f"[{self.profile_name}] Настройка админа {chat_admin.name} для чата {chat_link}")

                if not chat_admin.session_path.exists() or not chat_admin.json_path.exists():
                    logger.error(f"[{self.profile_name}] Файлы админа {chat_admin.name} не найдены")
                    return False

                # Создаем и подключаем админа
                from src.accounts.impl.account import Account
                chat_admin.account = Account(
                    session_path=chat_admin.session_path,
                    json_path=chat_admin.json_path
                )
                await chat_admin.account.create_client()

                if not await chat_admin.account.connect():
                    logger.error(f"[{self.profile_name}] Не удалось подключить админа {chat_admin.name}")
                    return False

                if not await chat_admin.account.client.is_user_authorized():
                    logger.error(f"[{self.profile_name}] Админ {chat_admin.name} не авторизован")
                    return False

                me = await chat_admin.account.client.get_me()
                logger.success(
                    f"[{self.profile_name}] Админ {chat_admin.name} подключен: {me.first_name} (@{me.username or 'без username'})")

            return True

        except Exception as e:
            logger.error(f"[{self.profile_name}] Ошибка настройки админов: {e}")
            return False

    async def _prepare_admins_in_chats(self) -> bool:
        """
        НОВОЕ: Подготовка каждого админа в его чате
        """
        for chat_link, chat_admin in self.chat_admins.items():
            logger.info(f"[{self.profile_name}] Подготовка админа {chat_admin.name} в чате {chat_link}")

            success = await ensure_main_admin_ready_in_chat(
                main_admin_account=chat_admin.account,
                admin_rights_manager=self.admin_rights_manager,
                chat_link=chat_link
            )

            if success:
                chat_admin.is_ready = True
                self.ready_chats.add(chat_link)
                logger.success(f"[{self.profile_name}] Админ {chat_admin.name} готов в чате: {chat_link}")
            else:
                logger.error(
                    f"[{self.profile_name}] Не удалось подготовить админа {chat_admin.name} в чате: {chat_link}")

        # Проверяем результаты
        if not self.ready_chats:
            logger.error(f"[{self.profile_name}] Ни один админ не готов! Прекращаем работу.")
            return False

        logger.success(
            f"[{self.profile_name}] Готовых чатов: {len(self.ready_chats)} из {len(self.chat_admins)}")
        return True

    async def _main_work_loop(self):
        """ГЛАВНЫЙ РАБОЧИЙ ЦИКЛ с периодическим сохранением"""
        # Задержка старта
        if self.config.delay_after_start > 0:
            await asyncio.sleep(self.config.delay_after_start)

        # Запускаем чаты
        await self._start_chats()

        if not self.chat_threads:
            logger.error(f"[{self.profile_name}] Нет запущенных потоков чатов!")
            return

        # ГЛАВНЫЙ ЦИКЛ: обработка команд + проверка потоков + периодическое сохранение
        last_save_time = datetime.now()
        save_interval = timedelta(minutes=5)  # Сохраняем каждые 5 минут

        while not self.stop_flag.is_set():
            try:
                # 1. Обрабатываем команды от воркеров
                try:
                    command = self.admin_command_queue.get_nowait()
                    await self._execute_admin_command(command)
                except queue.Empty:
                    pass

                # 2. Проверяем состояние потоков
                alive_threads = [t for t in self.chat_threads if t.is_alive()]

                if not alive_threads:
                    logger.info(f"💾 [{self.profile_name}] Все потоки завершены - СОХРАНЯЕМ прогресс...")
                    self._save_users_progress_to_file()

                    if self.total_processed > 0:
                        break
                    elif self.user_queue.empty():
                        break

                # 3. Периодическое сохранение прогресса
                current_time = datetime.now()
                if current_time - last_save_time >= save_interval:
                    logger.info(f"⏰ [{self.profile_name}] Периодическое сохранение прогресса...")
                    self._save_users_progress_to_file()
                    last_save_time = current_time

                # 4. Короткая пауза
                await asyncio.sleep(0.1)

            except Exception as e:
                logger.error(f"[{self.profile_name}] Ошибка главного цикла: {e}")
                await asyncio.sleep(1)

        # Ждем завершения всех потоков
        for thread in self.chat_threads:
            if thread.is_alive():
                thread.join(timeout=30)

        # ОБЯЗАТЕЛЬНО сохраняем прогресс в ЛЮБОМ случае завершения
        logger.info(f"💾 [{self.profile_name}] ОБЯЗАТЕЛЬНОЕ сохранение прогресса при завершении главного цикла...")
        self._save_users_progress_to_file()

        # Освобождаем все аккаунты модуля при завершении
        try:
            released_count = self.account_manager.release_all_module_accounts(f"admin_inviter_{self.profile_name}")
        except Exception as e:
            logger.error(f"[{self.profile_name}] Ошибка освобождения аккаунтов при завершении: {e}")

    async def _start_chats(self):
        """Запуск потоков чатов"""
        ready_chat_list = list(self.ready_chats)

        if not ready_chat_list:
            logger.error(f"[{self.profile_name}] Нет готовых чатов для запуска")
            return

        for i, chat_link in enumerate(ready_chat_list, 1):
            try:
                thread = ChatWorkerThread(
                    chat_id=i,
                    chat_link=chat_link,
                    parent=self
                )
                thread.start()
                self.chat_threads.append(thread)
                logger.success(
                    f"[{self.parent.profile_name}]-[Поток-{i}] Запущен чат: {chat_link} (Админ: {self.parent.chat_admins.get(chat_link, ChatAdmin('Неизвестен')).name})")

            except Exception as e:
                logger.error(f"[{self.profile_name}] Ошибка запуска чата {chat_link}: {e}")

    async def _execute_admin_command(self, command: AdminCommand):
        """
        ИСПРАВЛЕНО: Выполнение команды от воркера с правильным админом для чата
        """
        try:
            if command.chat_link not in self.ready_chats:
                logger.error(f"[{self.profile_name}] Чат {command.chat_link} не готов для работы с воркерами")
                command.response_queue.put(False)
                return

            # ИСПРАВЛЕНИЕ: Получаем правильного админа для этого чата
            chat_admin = self.chat_admins.get(command.chat_link)
            if not chat_admin or not chat_admin.is_ready:
                logger.error(f"[{self.profile_name}] Админ для чата {command.chat_link} не готов")
                command.response_queue.put(False)
                return

            if command.action == "GRANT_RIGHTS":
                from .admin_rights_manager import grant_worker_rights_directly

                chat_entity = await chat_admin.account.client.get_entity(command.chat_link)

                success = await grant_worker_rights_directly(
                    main_admin_client=chat_admin.account.client,
                    chat_entity=chat_entity,
                    worker_user_id=command.worker_user_id,
                    worker_user_access_hash=command.worker_access_hash,
                    worker_name=command.worker_name
                )

                command.response_queue.put(success)

                if success:
                    logger.success(
                        f"[{self.profile_name}] Права выданы воркеру {command.worker_name} админом {chat_admin.name}")
                else:
                    logger.error(f"[{self.profile_name}] Не удалось выдать права воркеру {command.worker_name}")

            elif command.action == "REVOKE_RIGHTS":
                from .admin_rights_manager import revoke_worker_rights_directly

                chat_entity = await chat_admin.account.client.get_entity(command.chat_link)

                await revoke_worker_rights_directly(
                    main_admin_client=chat_admin.account.client,
                    chat_entity=chat_entity,
                    worker_user_id=command.worker_user_id,
                    worker_name=command.worker_name
                )

                command.response_queue.put(True)

        except Exception as e:
            logger.error(f"[{self.profile_name}] Ошибка выполнения команды {command.action}: {e}")
            command.response_queue.put(False)

    async def _cleanup(self):
        """Очистка с ОБЯЗАТЕЛЬНЫМ сохранением прогресса"""
        try:
            # Останавливаем все
            self.admin_stop_event.set()

            # КРИТИЧЕСКИ ВАЖНО - сохраняем прогресс ПЕРЕД очисткой
            logger.info(f"💾 [{self.profile_name}] КРИТИЧЕСКОЕ сохранение прогресса в _cleanup...")
            self._save_users_progress_to_file()

            # Освобождаем все аккаунты модуля
            try:
                module_name = f"admin_inviter_{self.profile_name}"
                released_count = self.account_manager.release_all_module_accounts(module_name)
            except Exception as e:
                logger.error(f"[{self.profile_name}] Ошибка освобождения аккаунтов при очистке: {e}")

            # ИСПРАВЛЕНИЕ: Отключаем всех админов
            for chat_link, chat_admin in self.chat_admins.items():
                if chat_admin.account:
                    try:
                        if chat_admin.account.client and chat_admin.account.client.is_connected():
                            await chat_admin.account.disconnect()
                            logger.info(f"[{self.profile_name}] Отключен админ {chat_admin.name}")
                    except Exception as e:
                        logger.error(f"[{self.profile_name}] Ошибка отключения админа {chat_admin.name}: {e}")

        except Exception as e:
            logger.error(f"[{self.profile_name}] Ошибка в _cleanup: {e}")

    def _load_user_statuses(self):
        """Загружает статусы пользователей из файла"""
        try:
            profile_folder = Path(self.profile_data['folder_path'])
            status_file = profile_folder / "user_statuses.json"

            if status_file.exists():
                import json
                with open(status_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Загружаем пользователей
                for username, user_data in data.get('users', {}).items():
                    user = InviteUser(username=username)

                    # Правильная обработка enum статуса
                    status_value = user_data.get('status', 'NEW')
                    if isinstance(status_value, str):
                        # Пытаемся найти enum по значению
                        for status_enum in UserStatus:
                            if status_enum.value == status_value:
                                user.status = status_enum
                                break
                        else:
                            # Если не найден - устанавливаем NEW
                            user.status = UserStatus.NEW
                    else:
                        user.status = UserStatus.NEW

                    user.last_attempt = datetime.fromisoformat(user_data['last_attempt']) if user_data.get(
                        'last_attempt') else None
                    user.error_message = user_data.get('error_message')
                    self.processed_users[username] = user

                logger.success(f"[{self.profile_name}] Загружено статусов пользователей: {len(self.processed_users)}")
            else:
                logger.info(f"[{self.profile_name}] Файл статусов пользователей не найден, начинаем с чистого листа")

        except Exception as e:
            logger.error(f"[{self.profile_name}] Ошибка загрузки статусов пользователей: {e}")

    def _save_user_statuses(self):
        """Сохраняет статусы пользователей в файл"""
        try:
            profile_folder = Path(self.profile_data['folder_path'])
            status_file = profile_folder / "user_statuses.json"

            import json
            data = {
                'users': {},
                'last_updated': datetime.now().isoformat()
            }

            # Сохраняем статусы пользователей
            for username, user in self.processed_users.items():
                data['users'][username] = {
                    'status': user.status.value if hasattr(user.status, 'value') else str(user.status),
                    'last_attempt': user.last_attempt.isoformat() if user.last_attempt else None,
                    'error_message': user.error_message
                }

            with open(status_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            logger.success(f"[{self.profile_name}] Сохранено статусов пользователей: {len(self.processed_users)}")

        except Exception as e:
            logger.error(f"[{self.profile_name}] Ошибка сохранения статусов пользователей: {e}")

    def _generate_final_report(self):
        """Генерирует финальный отчет о работе"""
        try:
            profile_folder = Path(self.profile_data['folder_path'])
            report_file = profile_folder / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

            # Подсчитываем статистику
            total_users = len(self.processed_users)
            successful_invites = sum(1 for user in self.processed_users.values()
                                     if user.status == UserStatus.INVITED)

            # Статистика по статусам
            status_counts = {}
            for user in self.processed_users.values():
                status = user.status.value if hasattr(user.status, 'value') else str(user.status)
                status_counts[status] = status_counts.get(status, 0) + 1

            # Генерируем отчет
            report_lines = [
                f"ОТЧЕТ ПО АДМИН-ИНВАЙТИНГУ",
                f"=" * 50,
                f"Профиль: {self.profile_name}",
                f"Дата и время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                f"",
                f"ОБЩАЯ СТАТИСТИКА:",
                f"Всего пользователей обработано: {total_users}",
                f"Успешно приглашено: {successful_invites}",
                f"Процент успеха: {(successful_invites / total_users * 100):.2f}%" if total_users > 0 else "0.00%",
                f"",
                f"ИСПОЛЬЗОВАННЫЕ АДМИНЫ:",
            ]

            # Добавляем информацию об админах
            for chat_link, chat_admin in self.chat_admins.items():
                report_lines.append(f"  {chat_link} -> {chat_admin.name}")

            report_lines.extend([
                f"",
                f"ПОДРОБНАЯ СТАТИСТИКА ПО ЧАТАМ:",
            ])

            # ПОДРОБНАЯ СТАТИСТИКА ПО ЧАТАМ
            for chat_link, stats in self.chat_stats.items():
                success_rate = (stats['success'] / stats['total'] * 100) if stats['total'] > 0 else 0
                admin_name = self.chat_admins.get(chat_link, ChatAdmin("Неизвестен")).name

                report_lines.extend([
                    f"ЧАТ: {chat_link}",
                    f"Админ: {admin_name}",
                    f"Результат: {stats['success']}/{stats['total']} ({success_rate:.1f}%)",
                    f"",
                    f"ДОБАВЛЕННЫЕ ПОЛЬЗОВАТЕЛИ:",
                ])

                # Находим всех пользователей которые были успешно добавлены
                added_users = [username for username, user in self.processed_users.items()
                               if user.status == UserStatus.INVITED]

                if added_users:
                    for username in sorted(added_users):
                        report_lines.append(f"  @{username}")
                else:
                    report_lines.append("  (никого не добавили)")

                report_lines.extend([
                    f"",
                    f"-" * 30,
                    f""
                ])

            report_lines.extend([
                f"ОБЩАЯ СТАТИСТИКА ПО СТАТУСАМ ПОЛЬЗОВАТЕЛЕЙ:",
            ])

            # Добавляем статистику по статусам
            for status, count in sorted(status_counts.items()):
                percentage = (count / total_users * 100) if total_users > 0 else 0
                report_lines.append(f"  {status}: {count} ({percentage:.1f}%)")

            report_lines.extend([
                f"",
                f"СТАТИСТИКА ПО АККАУНТАМ:",
                f"Всего аккаунтов использовано: {len(self.account_stats)}",
                f"Успешно завершенных: {len(self.finished_successfully_accounts)}",
                f"Замороженных: {len(self.frozen_accounts)}",
                f"Списанных: {len(self.writeoff_accounts)}",
                f"Заблокированных на инвайты: {len(self.block_invite_accounts)}",
                f"Спам-блок: {len(self.spam_block_accounts)}",
                f"",
                f"=" * 50
            ])

            # Записываем отчет в файл
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(report_lines))

            logger.success(f"[{self.profile_name}] Отчет сохранен: {report_file}")

            # Также выводим краткую статистику в лог
            logger.success(
                f"[{self.profile_name}] ИТОГОВАЯ СТАТИСТИКА: {successful_invites}/{total_users} пользователей приглашено ({(successful_invites / total_users * 100):.1f}%)" if total_users > 0 else f"[{self.profile_name}] ИТОГОВАЯ СТАТИСТИКА: 0/0 пользователей приглашено (0.0%)")

        except Exception as e:
            logger.error(f"[{self.profile_name}] Ошибка генерации отчета: {e}")

    def update_account_stats(self, account_name: str, success: bool = False, spam_block: bool = False,
                             error: bool = False):
        """Обновление статистики"""
        if account_name not in self.account_stats:
            self.account_stats[account_name] = AccountStats(name=account_name)

        stats = self.account_stats[account_name]

        if success:
            stats.invites += 1
            self.total_success += 1
            if (self.config.success_per_account > 0 and stats.invites >= self.config.success_per_account):
                stats.status = 'finished'
                self.finished_accounts.add(account_name)
                self.finished_successfully_accounts.add(account_name)  # Помечаем для перемещения
                self.account_finish_times[account_name] = datetime.now()
                # Помечаем как обработанный
                self._mark_account_as_processed(account_name, "достигнут лимит успехов")

                # Обновляем статус в менеджере СРАЗУ
                self._update_account_status_in_manager_sync(account_name, "finished")

                mark_account_as_finished(self, account_name)

        if error:
            stats.errors += 1
            self.total_errors += 1

        if spam_block:
            stats.spam_blocks += 1
            if stats.spam_blocks >= self.config.acc_spam_limit:
                stats.status = 'spam_blocked'
                self.frozen_accounts.add(account_name)

        self.total_processed += 1


class ChatWorkerThread(threading.Thread):
    """Поток для одного чата - управляет воркерами с автоматической сменой аккаунтов"""

    def __init__(self, chat_id: int, chat_link: str, parent: AdminInviterProcess):
        super().__init__(name=f"Chat-{chat_id}")
        self.chat_id = chat_id
        self.chat_link = chat_link
        self.parent = parent
        self.chat_success = 0
        self.chat_total = 0  # Общее количество попыток в этом чате
        self.active_workers = []
        self.workers_lock = threading.Lock()

        # Инициализируем статистику чата
        if chat_link not in parent.chat_stats:
            parent.chat_stats[chat_link] = {"success": 0, "total": 0}

    def run(self):
        """Основной цикл чата"""
        # Проверяем готовность чата
        if self.chat_link not in self.parent.ready_chats:
            logger.error(f"[{self.parent.profile_name}]-[Поток-{self.chat_id}] Чат не готов: {self.chat_link}")
            return

        module_name = f"admin_inviter_{self.parent.profile_name}"

        try:
            while not self.parent.stop_flag.is_set():
                # Проверки лимитов
                if not check_chat_limits(self.parent, self.chat_success):
                    logger.info(f"[{self.parent.profile_name}]-[Поток-{self.chat_id}] Достигнут лимит чата")
                    break

                if self.parent.user_queue.empty():
                    logger.info(f"[{self.parent.profile_name}]-[Поток-{self.chat_id}] Нет пользователей")
                    break

                # Убираем мертвые воркеры
                with self.workers_lock:
                    self.active_workers = [w for w in self.active_workers if w.is_alive()]
                    active_count = len(self.active_workers)

                # Нужны новые воркеры?
                needed = self.parent.config.threads_per_chat - active_count
                if needed > 0:
                    # Проверка доступности аккаунтов
                    if not self.parent.check_accounts_availability():
                        # Если нет аккаунтов и нет активных воркеров - завершаем чат
                        if active_count == 0:
                            logger.info(
                                f"[{self.parent.profile_name}]-[Поток-{self.chat_id}] Нет аккаунтов и воркеров - завершаем")
                            break

                        # Иначе ждем немного и проверяем снова
                        time.sleep(10)
                        continue

                    # Запускаем новые воркеры (которые сами будут менять аккаунты)
                    for i in range(needed):
                        worker = WorkerThread(
                            worker_id=active_count + i + 1,
                            chat_thread=self,
                            module_name=module_name
                        )
                        worker.start()

                        with self.workers_lock:
                            self.active_workers.append(worker)

                        logger.success(
                            f"[{self.parent.profile_name}]-[Поток-{self.chat_id}] Запущен воркер-{active_count + i + 1}")

                # Пауза между проверками
                time.sleep(5)

            # Ждем завершения воркеров
            with self.workers_lock:
                workers_to_wait = self.active_workers.copy()

            for worker in workers_to_wait:
                if worker.is_alive():
                    worker.join(timeout=30)

            # Сохраняем прогресс при завершении чата
            logger.info(f"💾 [{self.parent.profile_name}]-[Поток-{self.chat_id}] Чат завершен - сохраняем прогресс...")
            self.parent._save_users_progress_to_file()

        except Exception as e:
            logger.error(f"[{self.parent.profile_name}]-[Поток-{self.chat_id}] Ошибка: {e}")
            # ДАЖЕ ПРИ ОШИБКЕ сохраняем прогресс
            logger.info(f"💾 [{self.parent.profile_name}]-[Поток-{self.chat_id}] Ошибка в чате - сохраняем прогресс...")
            self.parent._save_users_progress_to_file()


class WorkerThread(threading.Thread):
    """
    ИСПРАВЛЕННЫЙ воркер с автоматической сменой аккаунтов
    """

    def __init__(self, worker_id: int, chat_thread: ChatWorkerThread, module_name: str):
        super().__init__(name=f"Worker-{worker_id}")
        self.worker_id = worker_id
        self.chat_thread = chat_thread
        self.module_name = module_name
        self.current_account_data = None
        self.current_account_name = "НетАккаунта"
        self.worker_account = None

    def run(self):
        """Основной метод воркера - теперь управляет несколькими аккаунтами"""
        try:
            # Проверяем готовность чата
            if self.chat_thread.chat_link not in self.chat_thread.parent.ready_chats:
                logger.error(
                    f"[{self.chat_thread.parent.profile_name}]-[Поток-{self.chat_thread.chat_id}]-[Воркер-{self.worker_id}] Чат не готов: {self.chat_thread.chat_link}")
                return

            # Создаем event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # Запускаем логику с автоматической сменой аккаунтов
            loop.run_until_complete(self._worker_logic())

        except Exception as e:
            logger.error(
                f"[{self.chat_thread.parent.profile_name}]-[Поток-{self.chat_thread.chat_id}]-[Воркер-{self.worker_id}] Ошибка: {e}")
        finally:
            if 'loop' in locals():
                loop.close()

            # Финальное сохранение прогресса при завершении воркера
            logger.info(f"💾 [Воркер-{self.worker_id}] ФИНАЛЬНОЕ сохранение прогресса при завершении воркера...")
            self.chat_thread.parent._save_users_progress_to_file()

    async def _worker_logic(self):
        """Основная логика воркера с автоматической сменой аккаунтов"""
        chat_id = self.chat_thread.chat_id

        # ОСНОВНОЙ ЦИКЛ ВОРКЕРА - продолжает работать пока есть пользователи и аккаунты
        while not self.chat_thread.parent.stop_flag.is_set():

            # Проверяем есть ли пользователи для обработки
            if self.chat_thread.parent.user_queue.empty():
                logger.info(
                    f"[{self.chat_thread.parent.profile_name}]-[Поток-{chat_id}]-[Воркер-{self.worker_id}] Нет пользователей - завершаем воркер")
                break

            # Проверяем лимиты чата
            if not check_chat_limits(self.chat_thread.parent, self.chat_thread.chat_success):
                logger.info(
                    f"[{self.chat_thread.parent.profile_name}]-[Поток-{chat_id}]-[Воркер-{self.worker_id}] Достигнут лимит чата - завершаем воркер")
                break

            # ПОЛУЧАЕМ НОВЫЙ АККАУНТ для работы
            fresh_accounts = self.chat_thread.parent.get_fresh_accounts(self.module_name, 1)

            if not fresh_accounts:
                logger.warning(
                    f"[{self.chat_thread.parent.profile_name}]-[Поток-{chat_id}]-[Воркер-{self.worker_id}] Нет доступных аккаунтов - завершаем воркер")
                break

            # Обновляем данные аккаунта
            self.current_account_data = fresh_accounts[0]
            self.current_account_name = self.current_account_data.name
            self.worker_account = None

            logger.info(
                f"[{self.chat_thread.parent.profile_name}]-[Поток-{chat_id}]-[Воркер-{self.worker_id}] 🔄 Начинаем работу с аккаунтом: {self.current_account_name}")

            # РАБОТАЕМ С ТЕКУЩИМ АККАУНТОМ до его завершения
            account_finished = await self._work_with_current_account()

            if account_finished:
                logger.success(
                    f"[{self.chat_thread.parent.profile_name}]-[Поток-{chat_id}]-[Воркер-{self.worker_id}] ✅ Аккаунт {self.current_account_name} завершен, переходим к следующему")
                # Продолжаем цикл для получения нового аккаунта
                continue
            else:
                # Если аккаунт завершился по критической ошибке - завершаем воркер
                logger.error(
                    f"[{self.chat_thread.parent.profile_name}]-[Поток-{chat_id}]-[Воркер-{self.worker_id}] ❌ Критическая ошибка - завершаем воркер")
                break

    async def _work_with_current_account(self) -> bool:
        """
        Работает с текущим аккаунтом до его завершения

        Returns:
            True - если аккаунт успешно завершен (достиг лимита/проблемы), можно брать следующий
            False - если критическая ошибка, нужно завершить воркер
        """
        chat_id = self.chat_thread.chat_id
        client_connected = False
        rights_granted = False

        try:
            # 1. Проверяем файлы аккаунта
            session_path = self.current_account_data.account.session_path
            json_path = self.current_account_data.account.json_path

            if not Path(session_path).exists():
                logger.error(
                    f"[{self.chat_thread.parent.profile_name}]-[Поток-{chat_id}]-[{self.current_account_name}] Файл сессии не найден: {session_path}")
                await self._handle_problem("missing_files")
                return True  # Переходим к следующему аккаунту

            if not Path(json_path).exists():
                logger.error(
                    f"[{self.chat_thread.parent.profile_name}]-[Поток-{chat_id}]-[{self.current_account_name}] JSON файл не найден: {json_path}")
                await self._handle_problem("missing_files")
                return True  # Переходим к следующему аккаунту

            # 2. Создание и подключение аккаунта
            from src.accounts.impl.account import Account
            self.worker_account = Account(session_path=session_path, json_path=json_path)
            await self.worker_account.create_client()

            if not await self.worker_account.connect():
                logger.error(
                    f"[{self.chat_thread.parent.profile_name}]-[Поток-{chat_id}]-[{self.current_account_name}] Не подключился")
                await self._handle_problem("connection_failed")
                return True  # Переходим к следующему аккаунту

            client_connected = True

            if not await self.worker_account.client.is_user_authorized():
                logger.error(
                    f"[{self.chat_thread.parent.profile_name}]-[Поток-{chat_id}]-[{self.current_account_name}] Не авторизован")
                await self._handle_problem("unauthorized")
                return True  # Переходим к следующему аккаунту

            me = await self.worker_account.client.get_me()
            logger.success(
                f"[{self.chat_thread.parent.profile_name}]-[Поток-{chat_id}]-[{self.current_account_name}] Подключен: {me.first_name}")

            # 3. Вход в чат
            join_result = await self._join_chat()
            if join_result == "FROZEN_ACCOUNT":
                await self._handle_problem("frozen")
                return True  # Переходим к следующему аккаунту
            elif join_result != "SUCCESS":
                await self._handle_problem("dead")
                return True  # Переходим к следующему аккаунту

            # 4. Получение прав
            user_entity = await self.worker_account.client.get_entity('me')
            response_queue = queue.Queue()
            command = AdminCommand(
                action="GRANT_RIGHTS",
                worker_name=self.current_account_name,
                worker_user_id=user_entity.id,
                worker_access_hash=user_entity.access_hash,
                chat_link=self.chat_thread.chat_link,
                response_queue=response_queue
            )

            self.chat_thread.parent.admin_command_queue.put(command)

            try:
                rights_granted = response_queue.get(timeout=30)
            except queue.Empty:
                logger.error(
                    f"[{self.chat_thread.parent.profile_name}]-[Поток-{chat_id}]-[{self.current_account_name}] Таймаут получения прав")
                await self._handle_problem("dead")
                return True  # Переходим к следующему аккаунту

            if not rights_granted:
                logger.error(
                    f"[{self.chat_thread.parent.profile_name}]-[Поток-{chat_id}]-[{self.current_account_name}] Права не выданы")
                await self._handle_problem("dead")
                return True  # Переходим к следующему аккаунту

            logger.success(
                f"[{self.chat_thread.parent.profile_name}]-[Поток-{chat_id}]-[{self.current_account_name}] ✅ Права получены")

            # 5. ГЛАВНЫЙ ЦИКЛ ИНВАЙТИНГА для текущего аккаунта
            invites_count = 0

            while not self.chat_thread.parent.stop_flag.is_set():
                # Проверки лимитов
                if not check_account_limits(self.chat_thread.parent, self.current_account_name, invites_count):
                    logger.info(
                        f"[{self.chat_thread.parent.profile_name}]-[Поток-{chat_id}]-[{self.current_account_name}] Достигнут лимит аккаунта")
                    break

                if not check_chat_limits(self.chat_thread.parent, self.chat_thread.chat_success):
                    logger.info(
                        f"[{self.chat_thread.parent.profile_name}]-[Поток-{chat_id}]-[{self.current_account_name}] Достигнут лимит чата")
                    break

                # Получаем пользователя
                try:
                    user = self.chat_thread.parent.user_queue.get_nowait()
                except queue.Empty:
                    logger.info(
                        f"[{self.chat_thread.parent.profile_name}]-[Поток-{chat_id}]-[{self.current_account_name}] Нет пользователей")
                    break

                # Инвайтим пользователя
                try:
                    result = await self._invite_user(user)

                    if result == "SUCCESS":
                        invites_count += 1
                        self.chat_thread.chat_success += 1
                        self.chat_thread.chat_total += 1

                        # Обновляем статистику
                        self.chat_thread.parent.chat_stats[self.chat_thread.chat_link]["success"] += 1
                        self.chat_thread.parent.chat_stats[self.chat_thread.chat_link]["total"] += 1

                        logger.success(
                            f"[{self.chat_thread.parent.profile_name}]-[Поток-{chat_id}]-[{self.current_account_name}] 🎉 ИНВАЙТ #{invites_count}: @{user.username}")

                        # Сбрасываем счетчики ошибок при успехе
                        self.chat_thread.parent._check_account_error_limits(self.current_account_name, "success")
                        self.chat_thread.parent.update_account_stats(self.current_account_name, success=True)

                        # КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Проверяем достижение лимита успехов
                        if self.current_account_name in self.chat_thread.parent.finished_successfully_accounts:
                            logger.success(
                                f"[{self.chat_thread.parent.profile_name}]-[Поток-{chat_id}]-[{self.current_account_name}] ✅ ДОСТИГ ЛИМИТА УСПЕХОВ - завершаем аккаунт")

                            # Сохраняем прогресс
                            logger.info(
                                f"💾 [{self.chat_thread.parent.profile_name}]-[Поток-{chat_id}]-[{self.current_account_name}] Лимит успехов - сохраняем прогресс...")
                            self.chat_thread.parent._save_users_progress_to_file()

                            # Обновляем статус в менеджере
                            await self._update_account_status_in_manager("finished")

                            # ВАЖНО: Завершаем работу с ЭТИМ аккаунтом, но НЕ воркер
                            break  # Выходим из цикла инвайтинга для этого аккаунта

                    elif result == "WRITEOFF":
                        self.chat_thread.chat_total += 1
                        self.chat_thread.parent.chat_stats[self.chat_thread.chat_link]["total"] += 1

                        logger.warning(
                            f"[{self.chat_thread.parent.profile_name}]-[Поток-{chat_id}]-[{self.current_account_name}] ⚠️ СПИСАНИЕ: @{user.username}")

                        should_finish = self.chat_thread.parent._check_account_error_limits(self.current_account_name,
                                                                                            "writeoff")
                        if should_finish:
                            logger.error(
                                f"[{self.chat_thread.parent.profile_name}]-[Поток-{chat_id}]-[{self.current_account_name}] ❌ ПРЕВЫШЕН ЛИМИТ СПИСАНИЙ - завершаем аккаунт")

                            self.chat_thread.parent.writeoff_accounts.add(self.current_account_name)
                            self.chat_thread.parent._mark_account_as_processed(self.current_account_name,
                                                                               "лимит списаний")
                            await self._update_account_status_in_manager("writeoff")

                            # Сохраняем прогресс
                            logger.info(
                                f"💾 [{self.chat_thread.parent.profile_name}]-[Поток-{chat_id}]-[{self.current_account_name}] Лимит списаний - сохраняем прогресс...")
                            self.chat_thread.parent._save_users_progress_to_file()

                            await self._handle_problem("writeoff_limit")
                            break  # Завершаем этот аккаунт, переходим к следующему

                        self.chat_thread.parent.update_account_stats(self.current_account_name, error=True)

                    elif result == "SPAM_BLOCK":
                        self.chat_thread.chat_total += 1
                        self.chat_thread.parent.chat_stats[self.chat_thread.chat_link]["total"] += 1

                        logger.warning(
                            f"[{self.chat_thread.parent.profile_name}]-[Поток-{chat_id}]-[{self.current_account_name}] 🚫 СПАМ-БЛОК: @{user.username}")

                        should_finish = self.chat_thread.parent._check_account_error_limits(self.current_account_name,
                                                                                            "spam_block")
                        if should_finish:
                            logger.error(
                                f"[{self.chat_thread.parent.profile_name}]-[Поток-{chat_id}]-[{self.current_account_name}] ❌ ПРЕВЫШЕН ЛИМИТ СПАМ-БЛОКОВ - завершаем аккаунт")

                            self.chat_thread.parent.spam_block_accounts.add(self.current_account_name)
                            self.chat_thread.parent._mark_account_as_processed(self.current_account_name,
                                                                               "лимит спам-блоков")
                            await self._update_account_status_in_manager("frozen")

                            # Сохраняем прогресс
                            logger.info(
                                f"💾 [{self.chat_thread.parent.profile_name}]-[Поток-{chat_id}]-[{self.current_account_name}] Лимит спам-блоков - сохраняем прогресс...")
                            self.chat_thread.parent._save_users_progress_to_file()

                            await self._handle_problem("spam_limit")
                            break  # Завершаем этот аккаунт, переходим к следующему

                        self.chat_thread.parent.update_account_stats(self.current_account_name, spam_block=True,
                                                                     error=True)

                    elif result == "BLOCK_INVITE":
                        self.chat_thread.chat_total += 1
                        self.chat_thread.parent.chat_stats[self.chat_thread.chat_link]["total"] += 1

                        logger.warning(
                            f"[{self.chat_thread.parent.profile_name}]-[Поток-{chat_id}]-[{self.current_account_name}] 🔒 БЛОК ИНВАЙТ: @{user.username}")

                        should_finish = self.chat_thread.parent._check_account_error_limits(self.current_account_name,
                                                                                            "block_invite")
                        if should_finish:
                            logger.error(
                                f"[{self.chat_thread.parent.profile_name}]-[Поток-{chat_id}]-[{self.current_account_name}] ❌ ПРЕВЫШЕН ЛИМИТ БЛОКОВ ИНВАЙТОВ - завершаем аккаунт")

                            self.chat_thread.parent.block_invite_accounts.add(self.current_account_name)
                            self.chat_thread.parent._mark_account_as_processed(self.current_account_name,
                                                                               "лимит блоков инвайтов")
                            await self._update_account_status_in_manager("dead")

                            # Сохраняем прогресс
                            logger.info(
                                f"💾 [{self.chat_thread.parent.profile_name}]-[Поток-{chat_id}]-[{self.current_account_name}] Лимит блоков инвайтов - сохраняем прогресс...")
                            self.chat_thread.parent._save_users_progress_to_file()

                            await self._handle_problem("block_limit")
                            break  # Завершаем этот аккаунт, переходим к следующему

                        self.chat_thread.parent.update_account_stats(self.current_account_name, error=True)

                    elif result == "USER_ALREADY":
                        self.chat_thread.chat_total += 1
                        self.chat_thread.parent.chat_stats[self.chat_thread.chat_link]["total"] += 1

                        logger.warning(
                            f"[{self.chat_thread.parent.profile_name}]-[Поток-{chat_id}]-[{self.current_account_name}] 👥 УЖЕ В ЧАТЕ: @{user.username}")

                    else:  # Прочие ошибки
                        self.chat_thread.chat_total += 1
                        self.chat_thread.parent.chat_stats[self.chat_thread.chat_link]["total"] += 1

                except (PeerFloodError, FloodWaitError, AuthKeyUnregisteredError, SessionRevokedError) as e:
                    logger.error(
                        f"[{self.chat_thread.parent.profile_name}]-[Поток-{chat_id}]-[{self.current_account_name}] 💥 КРИТИЧЕСКАЯ ОШИБКА: {e}")

                    user.status = UserStatus.SPAM_BLOCK if 'flood' in str(e).lower() else UserStatus.ERROR
                    user.last_attempt = datetime.now()
                    user.error_message = str(e)
                    self.chat_thread.parent.processed_users[user.username] = user

                    problem_type = 'frozen' if 'flood' in str(e).lower() else 'dead'
                    self.chat_thread.parent._mark_account_as_processed(self.current_account_name,
                                                                       f"критическая ошибка: {problem_type}")

                    # Сохраняем прогресс
                    logger.info(
                        f"💾 [{self.chat_thread.parent.profile_name}]-[Поток-{chat_id}]-[{self.current_account_name}] Критическая ошибка - сохраняем прогресс...")
                    self.chat_thread.parent._save_users_progress_to_file()

                    await self._update_account_status_in_manager(problem_type)
                    await self._handle_problem(problem_type)
                    break  # Завершаем этот аккаунт, переходим к следующему

                # Задержка между инвайтами
                if self.chat_thread.parent.config.delay_between > 0:
                    await asyncio.sleep(self.chat_thread.parent.config.delay_between)

            # 6. Отзыв прав
            if rights_granted:
                await self._revoke_rights(user_entity.id)

            # 7. Финализация аккаунта
            await self._finalize_current_account(client_connected)

            # Аккаунт успешно завершен - можем переходить к следующему
            return True

        except Exception as e:
            logger.error(
                f"[{self.chat_thread.parent.profile_name}]-[Поток-{chat_id}]-[{self.current_account_name}] 💥 Критическая ошибка: {e}")

            # Помечаем аккаунт и сохраняем прогресс
            self.chat_thread.parent._mark_account_as_processed(self.current_account_name,
                                                               f"критическая ошибка: {str(e)[:50]}")
            logger.info(
                f"💾 [{self.chat_thread.parent.profile_name}]-[Поток-{chat_id}]-[{self.current_account_name}] Критическая ошибка воркера - сохраняем прогресс...")
            self.chat_thread.parent._save_users_progress_to_file()

            await self._handle_problem("dead")
            await self._finalize_current_account(client_connected)

            # При критической ошибке переходим к следующему аккаунту
            return True

    async def _finalize_current_account(self, client_connected: bool):
        """Финализация текущего аккаунта"""
        try:
            # Отключение
            if client_connected and self.worker_account:
                await self._disconnect()

            # Освобождение в менеджере
            try:
                self.chat_thread.parent.account_manager.release_account(self.current_account_name, self.module_name)
            except Exception as e:
                logger.error(
                    f"[{self.chat_thread.parent.profile_name}]-[{self.current_account_name}] Ошибка освобождения: {e}")

            # Перемещение файлов
            if (self.current_account_name in self.chat_thread.parent.writeoff_accounts or
                    self.current_account_name in self.chat_thread.parent.spam_block_accounts or
                    self.current_account_name in self.chat_thread.parent.block_invite_accounts or
                    self.current_account_name in self.chat_thread.parent.finished_successfully_accounts or
                    self.current_account_name in self.chat_thread.parent.frozen_accounts or
                    self.current_account_name in self.chat_thread.parent.blocked_accounts):

                try:
                    # Определяем тип папки
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
                    else:
                        problem_type = 'dead'

                    success = self.chat_thread.parent.account_mover.move_account(self.current_account_name,
                                                                                 problem_type)

                    if success:
                        logger.success(
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

    async def _join_chat(self):
        """Вход в чат"""
        try:
            result = await self.worker_account.join(self.chat_thread.chat_link)

            if result == "ALREADY_PARTICIPANT":
                logger.success(
                    f"[{self.chat_thread.parent.profile_name}]-[Поток-{self.chat_thread.chat_id}]-[{self.current_account_name}] Уже в чате")
                return "SUCCESS"
            elif result == "FROZEN_ACCOUNT":
                return "FROZEN_ACCOUNT"
            elif result == "CHAT_NOT_FOUND":
                return "CHAT_NOT_FOUND"
            elif isinstance(result, str) and result.startswith("ERROR:"):
                return "ERROR"
            else:
                logger.success(
                    f"[{self.chat_thread.parent.profile_name}]-[Поток-{self.chat_thread.chat_id}]-[{self.current_account_name}] Вступил в чат")
                return "SUCCESS"

        except Exception as e:
            logger.error(
                f"[{self.chat_thread.parent.profile_name}]-[Поток-{self.chat_thread.chat_id}]-[{self.current_account_name}] Ошибка входа в чат: {e}")
            return "ERROR"

    async def _invite_user(self, user: InviteUser) -> str:
        """
        Инвайт пользователя с обновлением в processed_users
        Возвращает: SUCCESS, WRITEOFF, SPAM_BLOCK, BLOCK_INVITE, ERROR
        """
        client = self.worker_account.client
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
                # Сохраняем пользователя для записи в файл
                self.chat_thread.parent.processed_users[username] = user
                return "ERROR"

            # Проверяем не находится ли пользователь уже в этом чате
            if old_common_chats > 0:
                try:
                    # Получаем user entity
                    user_entity = await client.get_input_entity(username)

                    # Запрашиваем общие чаты
                    common_chats_result = await client(GetCommonChatsRequest(
                        user_id=user_entity,
                        max_id=0,
                        limit=100
                    ))

                    # Получаем ID текущего чата
                    current_chat_entity = await client.get_input_entity(self.chat_thread.chat_link)
                    current_chat_id = None

                    # Получаем полную информацию о чате для получения ID
                    try:
                        chat_full = await client.get_entity(self.chat_thread.chat_link)
                        current_chat_id = chat_full.id
                    except Exception as e:
                        pass

                    # Проверяем есть ли среди общих чатов наш чат
                    if current_chat_id:
                        for chat in common_chats_result.chats:
                            if hasattr(chat, 'id') and chat.id == current_chat_id:
                                user.status = UserStatus.ALREADY_IN
                                user.last_attempt = datetime.now()
                                user.error_message = "Уже в чате"
                                # Сохраняем пользователя для записи в файл
                                self.chat_thread.parent.processed_users[username] = user
                                return "USER_ALREADY"

                except Exception as e:
                    # Если не удалось проверить - продолжаем инвайт
                    pass

            # Инвайт через админские права
            from telethon.tl.types import ChatAdminRights, InputChannel, InputUser
            from telethon.tl.functions.channels import EditAdminRequest

            # 1) подготовить InputChannel и InputUser
            input_channel = await client.get_input_entity(self.chat_thread.chat_link)
            input_user = await client.get_input_entity(username)

            # 2) задать все поля через именованные аргументы
            rights = ChatAdminRights(
                invite_users=True,
                anonymous=True,
            )

            # 3) выполнить запрос
            result = await client(EditAdminRequest(
                channel=input_channel,
                user_id=input_user,
                admin_rights=rights,
                rank="админ"  # можно пустую строку
            ))

            await asyncio.sleep(10)

            no_rights = ChatAdminRights(
                invite_users=False,
                anonymous=False,
            )

            # Забираем права через главного админа
            await client(EditAdminRequest(
                channel=input_channel,
                user_id=input_user,
                admin_rights=no_rights,
                rank=""  # Убираем звание
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
                    # Сохраняем пользователя для записи в файл
                    self.chat_thread.parent.processed_users[username] = user
                    return "WRITEOFF"
            except:
                pass

            # Успех
            user.status = UserStatus.INVITED
            user.last_attempt = datetime.now()
            # Сохраняем успешного пользователя для записи в файл
            self.chat_thread.parent.processed_users[username] = user
            return "SUCCESS"

        except (PeerFloodError, FloodWaitError):
            user.status = UserStatus.SPAM_BLOCK
            user.last_attempt = datetime.now()
            # Сохраняем пользователя для записи в файл
            self.chat_thread.parent.processed_users[username] = user
            return "SPAM_BLOCK"

        except UserPrivacyRestrictedError:
            user.status = UserStatus.PRIVACY
            user.last_attempt = datetime.now()
            # Сохраняем пользователя для записи в файл
            self.chat_thread.parent.processed_users[username] = user
            return "PRIVACY"

        except (UserDeactivatedBanError, UserDeactivatedError):
            user.status = UserStatus.NOT_FOUND
            user.last_attempt = datetime.now()
            # Сохраняем пользователя для записи в файл
            self.chat_thread.parent.processed_users[username] = user
            return "NOT_FOUND"

        except Exception as e:
            user.status = UserStatus.ERROR
            user.last_attempt = datetime.now()
            user.error_message = f"Ошибка: {str(e)[:50]}"
            # Сохраняем пользователя для записи в файл
            self.chat_thread.parent.processed_users[username] = user
            return "BLOCK_INVITE"

    async def _revoke_rights(self, worker_user_id: int):
        """Отзыв прав через команду админу"""
        try:
            response_queue = queue.Queue()
            command = AdminCommand(
                action="REVOKE_RIGHTS",
                worker_name=self.current_account_name,
                worker_user_id=worker_user_id,
                worker_access_hash=0,
                chat_link=self.chat_thread.chat_link,
                response_queue=response_queue
            )

            self.chat_thread.parent.admin_command_queue.put(command)

            try:
                response_queue.get(timeout=15)
                logger.success(
                    f"[{self.chat_thread.parent.profile_name}]-[Поток-{self.chat_thread.chat_id}]-[{self.current_account_name}] Права отозваны")
            except queue.Empty:
                logger.warning(
                    f"[{self.chat_thread.parent.profile_name}]-[Поток-{self.chat_thread.chat_id}]-[{self.current_account_name}] Таймаут отзыва прав")

        except Exception as e:
            logger.error(
                f"[{self.chat_thread.parent.profile_name}]-[Поток-{self.chat_thread.chat_id}]-[{self.current_account_name}] Ошибка отзыва прав: {e}")

    async def _update_account_status_in_manager(self, new_status: str):
        """
        Обновляет статус и путь аккаунта в менеджере чтобы он больше не выдавался как свободный
        """
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
                        'finished': WORK_TRAFFER_FOLDER / "Успешно_отработанные"
                    }

                    if new_status in folder_mapping:
                        new_folder = folder_mapping[new_status]
                        # Обновляем пути в account_data
                        account_data.account.session_path = new_folder / f"{self.current_account_name}.session"
                        account_data.account.json_path = new_folder / f"{self.current_account_name}.json"

                else:
                    logger.warning(
                        f"[{self.chat_thread.parent.profile_name}]-[Поток-{self.chat_thread.chat_id}]-[{self.current_account_name}] Аккаунт не найден в traffic_accounts менеджера")
            else:
                logger.warning(
                    f"[{self.chat_thread.parent.profile_name}]-[Поток-{self.chat_thread.chat_id}]-[{self.current_account_name}] У менеджера нет traffic_accounts")

        except Exception as e:
            logger.error(
                f"[{self.chat_thread.parent.profile_name}]-[Поток-{self.chat_thread.chat_id}]-[{self.current_account_name}] Ошибка обновления статуса в менеджере: {e}")

    async def _disconnect(self):
        """Отключение воркера"""
        try:
            if self.worker_account and self.worker_account.client:
                if self.worker_account.client.is_connected():
                    await self.worker_account.disconnect()
        except Exception as e:
            logger.error(
                f"[{self.chat_thread.parent.profile_name}]-[Поток-{self.chat_thread.chat_id}]-[{self.current_account_name}] Ошибка отключения: {e}")

    async def _handle_problem(self, problem_type: str):
        """Обработка проблемы"""
        try:
            # Помечаем как обработанный при любой проблеме
            self.chat_thread.parent._mark_account_as_processed(self.current_account_name, problem_type)

            if problem_type in ['frozen', 'spam_limit']:
                self.chat_thread.parent.frozen_accounts.add(self.current_account_name)
            else:
                self.chat_thread.parent.blocked_accounts.add(self.current_account_name)

        except Exception as e:
            logger.error(
                f"[{self.chat_thread.parent.profile_name}]-[Поток-{self.chat_thread.chat_id}]-[{self.current_account_name}] Ошибка пометки: {e}")