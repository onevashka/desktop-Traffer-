# src/modules/impl/inviter/admin_inviter.py
"""
Инвайтер через админку - использует бота для управления правами админов
ИСПРАВЛЕННАЯ ВЕРСИЯ с автоматической заменой воркеров как в классическом
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
            # ДОБАВЛЕНО: Сохраняем ссылку на текущий event loop
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

            # 3. Запускаем синхронную часть (потоки для чатов)
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
        """ИСПРАВЛЕНО: Запускает потоки для чатов с правильным получением воркеров"""
        # Задержка после старта
        if self.config.delay_after_start > 0:
            logger.info(f"[{self.profile_name}] Задержка {self.config.delay_after_start} сек...")
            self.stop_flag.wait(self.config.delay_after_start)

        # Получаем начальное количество чатов
        total_chats = self.chat_queue.qsize()
        self.initial_chats_count = total_chats
        logger.info(f"[{self.profile_name}] Всего чатов для обработки: {total_chats}")

        # НОВАЯ ЛОГИКА РАСЧЕТА АККАУНТОВ (как в классическом)
        # Рассчитываем общее количество требуемых успешных инвайтов
        total_invites_needed = total_chats * self.config.success_per_chat if self.config.success_per_chat > 0 else 999999
        logger.info(f"[{self.profile_name}] Требуется успешных инвайтов всего: {total_invites_needed}")

        # Рассчитываем сколько аккаунтов нужно исходя из лимита на аккаунт
        if self.config.success_per_account > 0:
            accounts_needed = (
                                          total_invites_needed + self.config.success_per_account - 1) // self.config.success_per_account
            logger.info(
                f"[{self.profile_name}] Расчетное количество аккаунтов: {accounts_needed} (по {self.config.success_per_account} инвайтов с аккаунта)")
        else:
            # Если лимит не установлен, используем старую логику
            accounts_needed = total_chats * self.config.threads_per_chat
            logger.info(
                f"[{self.profile_name}] Лимит на аккаунт не установлен, используем {accounts_needed} аккаунтов")

        # Проверяем доступность аккаунтов
        available_accounts = self.account_manager.get_free_accounts_count()
        logger.info(f"[{self.profile_name}] Доступно свободных аккаунтов: {available_accounts}")

        # Определяем сколько аккаунтов запросить на старте
        initial_accounts_to_request = min(accounts_needed, available_accounts,
                                          self.config.threads_per_chat * total_chats)

        if initial_accounts_to_request < accounts_needed:
            logger.warning(
                f"[{self.profile_name}] Недостаточно аккаунтов! Требуется: {accounts_needed}, доступно: {available_accounts}")
            logger.info(
                f"[{self.profile_name}] Будет использовано {initial_accounts_to_request} аккаунтов, работа может выполниться не полностью")

        # ИСПРАВЛЕНО: Загружаем главного админа из папки Админы как объект Account
        if not self.main_admin_account_name:
            logger.error(f"[{self.profile_name}] ❌ Главный админ не настроен")
            return

        # Создаем объект Account для главного админа
        main_admin_account = self._load_main_admin_account()
        if not main_admin_account:
            logger.error(
                f"[{self.profile_name}] ❌ Не удалось загрузить аккаунт главного админа: {self.main_admin_account_name}")
            return

        logger.info(f"[{self.profile_name}] Главный админ загружен: {self.main_admin_account_name}")

        # ИСПРАВЛЕНО: Получаем воркеров через _get_fresh_accounts (как в классическом)
        module_name = f"admin_inviter_{self.profile_name}"
        allocated_worker_accounts = self._get_fresh_accounts(module_name, initial_accounts_to_request)

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

                # ИСПРАВЛЕНО: Проверяем есть ли аккаунты для этого чата
                if worker_index >= len(allocated_worker_accounts):
                    # Пробуем получить еще аккаунты
                    additional_accounts = self._get_fresh_accounts(
                        module_name,
                        self.config.threads_per_chat
                    )

                    if additional_accounts:
                        allocated_worker_accounts.extend(additional_accounts)
                        logger.info(
                            f"[{self.profile_name}] Получено дополнительно {len(additional_accounts)} воркер-аккаунтов")
                    else:
                        # Возвращаем чат обратно в очередь
                        self.chat_queue.put(chat)
                        logger.warning(f"[{self.profile_name}] Нет воркеров для чата {chat}, отложен")
                        break

                # ИСПРАВЛЕНО: Выделяем воркеров для этого чата (как в классическом)
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

                # ИСПРАВЛЕНО: Передаем список объектов AccountData (не имена!)
                thread = AdminChatWorkerThread(
                    chat_id=chat_index + 1,
                    chat_link=chat,
                    main_admin_account=main_admin_account,  # Объект Account
                    worker_accounts=chat_worker_accounts,  # ← Теперь список AccountData!
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
                    f"(главный админ: {self.main_admin_account_name}, воркеров: {len(chat_worker_accounts)})"
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

    def _load_main_admin_account(self):
        """ИСПРАВЛЕНО: Загружает объект Account главного админа из папки Админы"""
        try:
            profile_folder = Path(self.profile_data['folder_path'])
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
            logger.error(f"🔍 Трассировка: {traceback.format_exc()}")
            return None

    def _get_fresh_accounts(self, module_name: str, count: int) -> List:
        """ИСПРАВЛЕНО: Получает только свежие (не отработанные) аккаунты (копия из классического)"""
        # Проверяем и очищаем аккаунты с истекшей 24-часовой меткой
        self._clean_expired_accounts()

        # Получаем аккаунты от менеджера
        all_accounts = self.account_manager.get_free_accounts(module_name, count * 2)  # Запрашиваем больше с запасом

        if not all_accounts:
            return []

        # Фильтруем отработанные аккаунты
        fresh_accounts = []
        for account in all_accounts:
            if account.name not in self.finished_accounts:
                fresh_accounts.append(account)
                if len(fresh_accounts) >= count:
                    break
            else:
                # Возвращаем отработанный аккаунт обратно
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

        logger.info(f"\n📊 СТАТИСТИКА ПО АККАУНТАМ:")
        for account_name, stats in self.account_stats.items():
            status_icon = "✅" if stats.status == 'finished' else "⚡" if stats.status == 'working' else "❌"
            logger.info(
                f"   {status_icon} {account_name}: инвайтов={stats.invites}, ошибок={stats.errors}, спамблоков={stats.spam_blocks}, статус={stats.status}")

        if self.finished_accounts:
            logger.info(f"\n🏁 ОТРАБОТАВШИЕ АККАУНТЫ: {len(self.finished_accounts)}")
            for account_name in self.finished_accounts:
                if account_name in self.account_finish_times:
                    finish_time = self.account_finish_times[account_name]
                    next_available = finish_time + timedelta(hours=24)
                    logger.info(f"   - {account_name} (доступен с {next_available.strftime('%H:%M:%S')})")

        if self.frozen_accounts:
            logger.warning(f"\nЗАМОРОЖЕННЫЕ АККАУНТЫ: {len(self.frozen_accounts)}")
            for frozen_account in self.frozen_accounts:
                logger.warning(f"   - {frozen_account}")

        logger.info("=" * 60)


class AdminChatWorkerThread(threading.Thread):
    """ПЕРЕПИСАНО: Рабочий поток для одного чата с ЦИКЛИЧЕСКОЙ работой воркеров как в классическом"""

    def __init__(self, chat_id: int, chat_link: str, main_admin_account,
                 worker_accounts: List, parent: AdminInviterProcess,  # ← Список AccountData!
                 profile_name: str, bot_manager: BotManager,
                 admin_rights_manager: AdminRightsManager):
        super().__init__(name=f"AdminChat-{chat_id}")
        self.chat_id = chat_id
        self.chat_link = chat_link

        # ИСПРАВЛЕНО: Правильно обрабатываем объект Account
        if hasattr(main_admin_account, 'name'):
            # Это объект Account
            self.main_admin_account = main_admin_account
            self.main_admin_account_name = main_admin_account.name
            logger.debug(f"Получен объект Account главного админа: {self.main_admin_account_name}")
        else:
            # Это строка с именем (legacy)
            self.main_admin_account = None
            self.main_admin_account_name = main_admin_account
            logger.debug(f"Получено имя главного админа: {self.main_admin_account_name}")

        # ИСПРАВЛЕНО: Теперь worker_accounts - это список AccountData объектов
        self.worker_accounts = worker_accounts  # Список AccountData для циклической работы
        self.parent = parent
        self.profile_name = profile_name

        # ИЗМЕНЕНИЕ: Сохраняем токен бота и создаем локальные менеджеры
        self.bot_token = parent.bot_token
        self.bot_manager = None
        self.admin_rights_manager = None
        self.main_loop = None

        # Статистика чата
        self.chat_success = 0
        self.chat_errors = 0
        self.chat_processed = 0

        # Состояние главного админа
        self.main_admin_has_rights = False

        # ID чата для проверки общих чатов
        self.chat_telegram_id = None

        # НОВОЕ: Флаги остановки чата (как в классическом)
        self.chat_stop_reason = None
        self.stop_all_workers = False

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
            logger.error(f"🔍 Трассировка: {traceback.format_exc()}")
        finally:
            if loop:
                loop.close()

    async def _work(self):
        """ПЕРЕПИСАНО: Основная работа с чатом через админку - с ЦИКЛИЧЕСКОЙ заменой воркеров"""
        logger.info(f"[{self.profile_name}]-[AdminChat-{self.chat_link}] 🤖 Начинаем работу через админку")
        logger.info(
            f"[{self.profile_name}]-[AdminChat-{self.chat_link}] Доступно воркеров: {len(self.worker_accounts)}")

        try:
            # НОВОЕ: 1. Создаем локальный bot manager
            if not await self._initialize_local_bot():
                logger.error(
                    f"[{self.profile_name}]-[AdminChat-{self.chat_link}] ❌ Не удалось инициализировать локальный бот")
                return

            # 2. Подготавливаем главного админа
            if not await self._setup_main_admin():
                logger.error(
                    f"[{self.profile_name}]-[AdminChat-{self.chat_link}] ❌ Не удалось настроить главного админа")
                return

            # 3. НОВАЯ ЛОГИКА: Циклическая работа с воркерами как в классическом
            await self._work_with_workers_cyclically()

        except Exception as e:
            logger.error(f"[{self.profile_name}]-[AdminChat-{self.chat_link}] ❌ Ошибка в работе: {e}")
            logger.error(f"🔍 Трассировка: {traceback.format_exc()}")
        finally:
            # 4. Финальная очистка - забираем права у главного админа
            await self._cleanup_main_admin()

            # НОВОЕ: 5. Отключаем локальный бот
            if self.bot_manager:
                await self.bot_manager.disconnect()

        logger.info(f"[{self.profile_name}]-[AdminChat-{self.chat_link}] 🏁 Работа завершена")
        logger.info(
            f"   Статистика: обработано={self.chat_processed}, успешно={self.chat_success}, ошибок={self.chat_errors}")

    async def _work_with_workers_cyclically(self):
        """НОВЫЙ МЕТОД: Циклическая работа с воркерами с автозаменой (как в классическом)"""
        logger.info(f"[{self.profile_name}]-[AdminChat-{self.chat_link}] 🔄 Запуск циклической работы с воркерами")

        # Флаг завершения работы чата
        chat_completed = False

        # Счетчик активных воркеров для этого чата
        active_workers = []
        active_workers_lock = threading.Lock()

        # Предварительно создаем клиенты в текущем event loop
        logger.info(f"[{self.profile_name}]-[AdminChat-{self.chat_link}] Инициализируем клиенты воркеров...")
        for account_data in self.worker_accounts:
            try:
                await account_data.account.create_client()
            except Exception as e:
                logger.error(f"[{self.profile_name}] Ошибка создания клиента для воркера {account_data.name}: {e}")

        # ГЛАВНЫЙ ЦИКЛ: Пока не завершена работа с чатом
        while not chat_completed and not self.parent.stop_flag.is_set():
            # Запускаем воркеров в отдельных потоках
            worker_threads = []

            for i, account_data in enumerate(self.worker_accounts):
                # Проверяем не отработан ли уже аккаунт
                if account_data.name in self.parent.finished_accounts:
                    logger.info(
                        f"[{self.profile_name}]-[AdminChat-{self.chat_link}] Воркер {account_data.name} уже отработан, пропускаем")
                    continue

                # Создаем поток для каждого воркера
                worker_thread = threading.Thread(
                    target=self._run_worker_in_thread,
                    args=(i + 1, account_data, active_workers, active_workers_lock),
                    name=f"AdminChat-{self.chat_link}-Worker-{i + 1}"
                )
                worker_thread.start()
                worker_threads.append(worker_thread)

            logger.info(
                f"[{self.profile_name}]-[AdminChat-{self.chat_link}] Запущено {len(worker_threads)} потоков воркеров")

            # Проверяем статус периодически (КАК В КЛАССИЧЕСКОМ)
            while not self.parent.stop_flag.is_set():
                # Ждем немного
                await asyncio.sleep(2)

                # Проверяем флаг остановки чата
                if self.stop_all_workers:
                    logger.warning(
                        f"[{self.profile_name}]-[AdminChat-{self.chat_link}] Остановка всех воркеров. Причина: {self.chat_stop_reason}")
                    chat_completed = True
                    break

                # Проверяем сколько воркеров еще работает
                with active_workers_lock:
                    still_working = len(active_workers)

                if still_working == 0:
                    logger.info(f"[{self.profile_name}]-[AdminChat-{self.chat_link}] Все воркеры завершили работу")
                    break

                # Проверяем условия завершения
                if self.parent.config.success_per_chat > 0 and self.chat_success >= self.parent.config.success_per_chat:
                    logger.success(
                        f"[{self.profile_name}]-[AdminChat-{self.chat_link}] Достигнут лимит успешных инвайтов: {self.chat_success}")
                    chat_completed = True
                    break

                if self.parent.user_queue.empty():
                    logger.info(
                        f"[{self.profile_name}]-[AdminChat-{self.chat_link}] Закончились пользователи для инвайта")
                    # Даем воркерам доработать текущих пользователей
                    await asyncio.sleep(5)
                    chat_completed = True
                    break

            # Освобождаем аккаунты которые закончили работу
            module_name = f"admin_inviter_{self.parent.profile_name}"
            released_count = 0

            for account_data in self.worker_accounts:
                # Проверяем не работает ли еще этот аккаунт
                account_working = False
                with active_workers_lock:
                    account_working = account_data.name in active_workers

                if not account_working:
                    self.parent.account_manager.release_account(account_data.name, module_name)
                    released_count += 1

            logger.info(
                f"[{self.profile_name}]-[AdminChat-{self.chat_link}] Освобождено завершивших работу воркеров: {released_count}")

            # Проверяем нужно ли продолжать работу
            if chat_completed:
                break

            # Проверяем специальные случаи остановки чата
            if self.stop_all_workers:
                logger.warning(
                    f"[{self.profile_name}]-[AdminChat-{self.chat_link}] Чат остановлен. Причина: {self.chat_stop_reason}")
                break

            # КЛЮЧЕВАЯ ЛОГИКА: Если есть пользователи и работа не завершена - запрашиваем новых воркеров
            if not self.parent.user_queue.empty():
                logger.info(
                    f"[{self.profile_name}]-[AdminChat-{self.chat_link}] Запрашиваем новых воркеров для продолжения работы")

                # Фильтруем отработанные аккаунты
                available_count = self.parent.account_manager.get_free_accounts_count()
                finished_count = len(self.parent.finished_accounts)

                logger.info(
                    f"[{self.profile_name}]-[AdminChat-{self.chat_link}] Доступно аккаунтов: {available_count}, отработано: {finished_count}")

                # Получаем новых воркеров через метод с фильтрацией
                new_worker_accounts = self.parent._get_fresh_accounts(
                    module_name,
                    self.parent.config.threads_per_chat
                )

                if not new_worker_accounts:
                    logger.warning(
                        f"[{self.profile_name}]-[AdminChat-{self.chat_link}] Нет свободных неотработанных воркеров")
                    chat_completed = True
                    break

                # Инициализируем клиенты для новых воркеров
                logger.info(
                    f"[{self.profile_name}]-[AdminChat-{self.chat_link}] Инициализируем клиенты для новых воркеров...")
                for account_data in new_worker_accounts:
                    try:
                        await account_data.account.create_client()
                    except Exception as e:
                        logger.error(f"Ошибка создания клиента для воркера {account_data.name}: {e}")

                self.worker_accounts = new_worker_accounts
                logger.info(
                    f"[{self.profile_name}]-[AdminChat-{self.chat_link}] Получено новых активных воркеров: {len(new_worker_accounts)}")

        # Финальная очистка - ждем оставшиеся воркеры
        logger.info(f"🧹 [{self.profile_name}]-[AdminChat-{self.chat_link}] Ожидаем завершения оставшихся воркеров...")

        # Даем воркерам время завершиться
        await asyncio.sleep(5)

        # Освобождаем все оставшиеся воркеры
        module_name = f"admin_inviter_{self.parent.profile_name}"
        for account_data in self.worker_accounts:
            self.parent.account_manager.release_account(account_data.name, module_name)

        logger.info(f"[{self.profile_name}]-[AdminChat-{self.chat_link}] Циклическая работа завершена")

    def _run_worker_in_thread(self, worker_id: int, account_data, active_workers: list, lock: threading.Lock):
        """НОВЫЙ МЕТОД: Обертка для запуска воркера в отдельном потоке (как в классическом)"""
        # Добавляем себя в список активных
        with lock:
            active_workers.append(account_data.name)

        try:
            # Используем loop из AdminChatWorkerThread
            chat_loop = self.main_loop

            # Запускаем корутину в loop чата из другого потока
            future = asyncio.run_coroutine_threadsafe(
                self._run_worker(worker_id, account_data),
                chat_loop
            )

            # Ждем завершения
            future.result()

        except Exception as e:
            logger.error(f"[{self.profile_name}]-[AdminWorker-{worker_id}] Ошибка в потоке: {e}")
        finally:
            # Удаляем себя из списка активных
            with lock:
                if account_data.name in active_workers:
                    active_workers.remove(account_data.name)

            # Освобождаем аккаунт через loop чата
            try:
                module_name = f"admin_inviter_{self.parent.profile_name}"
                asyncio.run_coroutine_threadsafe(
                    self._release_account_async(account_data.name, module_name),
                    chat_loop
                ).result(timeout=5)
            except Exception as e:
                logger.error(
                    f"[{self.profile_name}]-[AdminWorker-{worker_id}] Ошибка освобождения воркера {account_data.name}: {e}")

    async def _release_account_async(self, account_name: str, module_name: str):
        """Асинхронное освобождение аккаунта"""
        self.parent.account_manager.release_account(account_name, module_name)
        logger.info(f"Воркер {account_name} освобожден")

    async def _run_worker(self, worker_id: int, account_data):
        """НОВЫЙ МЕТОД: Воркер для инвайтинга с проверкой лимитов (как в классическом)"""
        worker_name = account_data.name
        worker_account = account_data.account

        logger.info(
            f"[{self.profile_name}]-[AdminChat-{self.chat_link}]-[Worker-{worker_id}] Запуск с воркером {worker_name}")

        try:
            # Клиент уже должен быть создан в основном потоке
            if not worker_account.client:
                logger.error(
                    f"[{self.profile_name}]-[Worker-{worker_id}]-[{worker_name}] Клиент не создан для воркера")
                return

            # Подключаемся
            if not await worker_account.connect():
                logger.error(
                    f"[{self.profile_name}]-[Worker-{worker_id}]-[{worker_name}] Не удалось подключить воркера")
                return

            # Проверяем авторизацию
            if not await worker_account.client.is_user_authorized():
                logger.error(
                    f"[{self.profile_name}]-[Worker-{worker_id}]-[{worker_name}] Воркер не авторизован")
                await worker_account.disconnect()
                return

            # Получаем информацию о воркере для проверки
            try:
                me = await worker_account.client.get_me()
                logger.info(
                    f"[{self.profile_name}]-[Worker-{worker_id}]-[{worker_name}] Подключен как {me.first_name} {me.last_name or ''} (@{me.username or 'no_username'})")
            except Exception as e:
                logger.error(
                    f"[{self.profile_name}]-[Worker-{worker_id}]-[{worker_name}] Ошибка получения информации о воркере: {e}")
                await worker_account.disconnect()
                return

            # Присоединяемся к чату
            join_result = await self._join_chat(worker_account, self.chat_link)

            # Обрабатываем результат присоединения
            if join_result == "STOP_CHAT":
                logger.warning(
                    f"[{self.profile_name}]-[Worker-{worker_id}]-[{worker_name}] Остановка всех воркеров чата. Причина: {self.chat_stop_reason}")
                self.stop_all_workers = True
                await worker_account.disconnect()
                return
            elif join_result == "FROZEN_ACCOUNT":
                logger.error(
                    f"[{self.profile_name}]-[Worker-{worker_id}]-[{worker_name}] Воркер заморожен, завершаем работу этого воркера")
                await worker_account.disconnect()
                return
            elif join_result != "SUCCESS":
                logger.error(
                    f"[{self.profile_name}]-[Worker-{worker_id}]-[{worker_name}] Не удалось присоединиться к чату")
                await worker_account.disconnect()
                return

            # Получаем user_id воркера
            user_entity = await worker_account.client.get_entity('me')
            user_id = user_entity.id

            # ВЫДАЕМ ПРАВА ВОРКЕРУ
            rights_granted = await self.admin_rights_manager.grant_worker_rights(
                self.chat_link, user_id, worker_name
            )

            if not rights_granted:
                logger.error(
                    f"[{self.profile_name}]-[Worker-{worker_id}]-[{worker_name}] ❌ Не удалось выдать права воркеру, завершаем")
                await worker_account.disconnect()
                return

            logger.info(
                f"[{self.profile_name}]-[Worker-{worker_id}]-[{worker_name}] ✅ Воркер получил права")

            invites_count = 0
            errors_count = 0

            # ОСНОВНОЙ ЦИКЛ ИНВАЙТИНГА (КАК В КЛАССИЧЕСКОМ)
            while not self.parent.stop_flag.is_set() and not self.stop_all_workers:
                # ВАЖНО: Проверяем достиг ли аккаунт лимита
                account_stats = self.parent.account_stats.get(worker_name)
                if account_stats and account_stats.status == 'finished':
                    logger.info(
                        f"[{self.profile_name}]-[Worker-{worker_id}]-[{worker_name}] Воркер достиг лимита, завершаем работу")
                    break

                # Проверяем не заблокирован ли аккаунт за спам
                if account_stats and account_stats.status == 'spam_blocked':
                    logger.error(
                        f"[{self.profile_name}]-[Worker-{worker_id}]-[{worker_name}] Воркер заблокирован за спам, завершаем работу")
                    break

                # Проверяем лимит успешных для чата
                if self.parent.config.success_per_chat > 0:
                    if self.chat_success >= self.parent.config.success_per_chat:
                        logger.info(
                            f"[{self.profile_name}]-[AdminChat-{self.chat_link}] Достигнут лимит успешных инвайтов для чата: {self.chat_success}")
                        break

                # Проверяем лимит для аккаунта
                if self.parent.config.success_per_account > 0:
                    if invites_count >= self.parent.config.success_per_account:
                        logger.info(
                            f"[{self.profile_name}]-[Worker-{worker_id}] Достигнут лимит инвайтов для воркера: {invites_count}")
                        break

                # Получаем пользователя
                try:
                    user = self.parent.user_queue.get_nowait()
                except queue.Empty:
                    logger.info(f"[{self.profile_name}]-[Worker-{worker_id}] Очередь пуста")
                    break

                # Инвайтим пользователя
                success = await self._invite_user(user, worker_account, worker_name, worker_id)

                if success:
                    invites_count += 1
                    self.chat_success += 1
                else:
                    errors_count += 1

                self.chat_processed += 1

                # Обновляем статистику аккаунта (проверка лимитов происходит внутри)
                self.parent.update_account_stats(
                    worker_name,
                    success=success,
                    spam_block=(user.status == UserStatus.SPAM_BLOCK),
                    error=(not success)
                )

                # Задержка между инвайтами
                if self.parent.config.delay_between > 0:
                    await asyncio.sleep(self.parent.config.delay_between)

            # ЗАБИРАЕМ ПРАВА У ВОРКЕРА
            try:
                await self.admin_rights_manager.revoke_worker_rights(
                    self.chat_telegram_id, user_id, worker_name
                )
                logger.info(
                    f"[{self.profile_name}]-[Worker-{worker_id}]-[{worker_name}] 🔒 Права воркера отозваны")
            except Exception as e:
                logger.error(f"[{self.profile_name}]-[Worker-{worker_id}]-[{worker_name}] ❌ Ошибка отзыва прав: {e}")

            logger.info(
                f"[{self.profile_name}]-[Worker-{worker_id}] Воркер завершен. Инвайтов: {invites_count}, ошибок: {errors_count}")

        except Exception as e:
            logger.error(f"[{self.profile_name}]-[Worker-{worker_id}] Критическая ошибка: {e}")
        finally:
            # Отключаемся от Telegram
            try:
                await worker_account.disconnect()
                await asyncio.sleep(30)
            except:
                pass

    async def _initialize_local_bot(self) -> bool:
        """Инициализирует локальный bot manager для этого потока"""
        try:
            logger.info(f"[{self.profile_name}]-[AdminChat-{self.chat_link}] 🤖 Инициализация локального бота...")

            # Создаем свой bot manager
            self.bot_manager = BotManager(
                bot_token=self.bot_token,
                proxy_url=None  # TODO: добавить прокси если нужно
            )

            # Подключаемся
            if not await self.bot_manager.connect():
                logger.error(
                    f"[{self.profile_name}]-[AdminChat-{self.chat_link}] ❌ Не удалось подключиться к локальному боту")
                return False

            # Создаем admin rights manager
            self.admin_rights_manager = AdminRightsManager(
                bot_manager=self.bot_manager
            )

            logger.info(
                f"[{self.profile_name}]-[AdminChat-{self.chat_link}] ✅ Локальный бот инициализирован: @{self.bot_manager.bot_username}")
            return True

        except Exception as e:
            logger.error(
                f"[{self.profile_name}]-[AdminChat-{self.chat_link}] ❌ Ошибка инициализации локального бота: {e}")
            logger.error(f"🔍 Трассировка: {traceback.format_exc()}")
            return False

    async def _setup_main_admin(self) -> bool:
        """Настраивает главного админа: заход в чат + получение прав от бота"""
        try:
            logger.info(
                f"[{self.profile_name}]-[AdminChat-{self.chat_link}] 👑 Настройка главного админа: {self.main_admin_account_name}")

            # Проверяем есть ли уже объект Account
            if self.main_admin_account is None:
                logger.info(
                    f"[{self.profile_name}]-[AdminChat-{self.chat_link}] 🔍 Загружаем главного админа из папки Админы")
                self.main_admin_account = self._load_admin_from_folder()

                if not self.main_admin_account:
                    logger.error(
                        f"[{self.profile_name}]-[AdminChat-{self.chat_link}] ❌ Не удалось загрузить аккаунт главного админа")
                    return False
            else:
                logger.info(
                    f"[{self.profile_name}]-[AdminChat-{self.chat_link}] ✅ Объект Account главного админа уже готов")

            # Создаем клиент если нужно
            if not self.main_admin_account.client:
                await self.main_admin_account.create_client()

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

            # Получаем user_id главного админа
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

            # ИЗМЕНЕНО: Выдаем права напрямую в локальном потоке (убрали run_coroutine_threadsafe)
            logger.info(
                f"[{self.profile_name}]-[AdminChat-{self.chat_link}] 🔧 Выдача прав через локальный admin_rights_manager...")

            success = await self.admin_rights_manager.grant_main_admin_rights(
                self.chat_telegram_id, user_id, self.main_admin_account_name
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
            logger.error(f"🔍 Трассировка: {traceback.format_exc()}")
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
            logger.error(f"🔍 Трассировка: {traceback.format_exc()}")
            return None

    async def _cleanup_main_admin(self):
        """Финальная очистка - забираем права у главного админа"""
        try:
            if self.main_admin_has_rights and self.admin_rights_manager:
                logger.info(f"[{self.profile_name}]-[AdminChat-{self.chat_link}] 🧹 Забираем права у главного админа")

                # ИЗМЕНЕНО: Забираем права напрямую
                await self.admin_rights_manager.revoke_main_admin_rights(self.chat_link)

                logger.info(f"[{self.profile_name}]-[AdminChat-{self.chat_link}] ✅ Права главного админа отозваны")
                self.main_admin_has_rights = False

            # ИСПРАВЛЕНО: Отключаем аккаунт напрямую, не через account_manager
            if self.main_admin_account:
                try:
                    await self.main_admin_account.disconnect()
                    logger.info(f"[{self.profile_name}]-[AdminChat-{self.chat_link}] ✅ Главный админ отключен")
                except Exception as e:
                    logger.warning(
                        f"[{self.profile_name}]-[AdminChat-{self.chat_link}] ⚠️ Ошибка отключения главного админа: {e}")

                self.main_admin_account = None

        except Exception as e:
            logger.error(f"[{self.profile_name}]-[AdminChat-{self.chat_link}] ❌ Ошибка очистки главного админа: {e}")
            logger.error(f"🔍 Трассировка: {traceback.format_exc()}")

    async def _join_chat(self, account, chat_link: str):
        """Заходит в чат"""
        try:
            result = await account.join(chat_link)

            # Анализируем результат
            if result == "ALREADY_PARTICIPANT":
                logger.info(
                    f"[{self.profile_name}]-[AdminChat-{self.chat_link}] Уже в чате {chat_link}")
                return "SUCCESS"

            elif result == "FROZEN_ACCOUNT":
                logger.error(f"[{self.profile_name}]-[AdminChat-{self.chat_link}] Аккаунт заморожен")
                return "FROZEN_ACCOUNT"

            elif result == "CHAT_NOT_FOUND":
                logger.error(
                    f"[{self.profile_name}]-[AdminChat-{self.chat_link}] Чат не найден: {chat_link}")
                self.chat_stop_reason = "Чат не найден"
                return "STOP_CHAT"

            elif result == "REQUEST_SENT":
                logger.warning(
                    f"[{self.profile_name}]-[AdminChat-{self.chat_link}] Отправлен запрос на вступление в {chat_link}")
                return False

            elif result == "FLOOD_WAIT":
                logger.warning(
                    f"[{self.profile_name}]-[AdminChat-{self.chat_link}] Нужно подождать перед присоединением в {chat_link}")
                return False

            elif isinstance(result, str) and result.startswith("ERROR:"):
                logger.error(f"❌ [{self.profile_name}]-[AdminChat-{self.chat_link}] Ошибка: {result}")
                return False

            else:
                # Успешно присоединились
                logger.info(
                    f"[{self.profile_name}]-[AdminChat-{self.chat_link}] {account.name} присоединился к чату {chat_link}")

                # Сохраняем информацию о чате
                if hasattr(result, 'id'):
                    self.chat_telegram_id = result.id

                # Задержка после присоединения
                if self.parent.config.delay_after_start > 0:
                    await asyncio.sleep(self.parent.config.delay_after_start)

                return "SUCCESS"

        except Exception as e:
            logger.error(
                f"[{self.profile_name}]-[AdminChat-{self.chat_link}] Ошибка присоединения к чату {chat_link}: {e}")
            return False

    async def _invite_user(self, user: InviteUser, account, account_name: str, worker_id: int) -> bool:
        """Инвайт пользователя через Telethon"""
        client = account.client

        if not client or not client.is_connected():
            logger.error(f"❌ [{self.profile_name}]-[Worker-{worker_id}]-[{account_name}] Клиент не подключен")
            return False

        username = user.username
        if username.startswith('@'):
            username = username[1:]

        logger.info(
            f"[{self.profile_name}]-[Worker-{worker_id}]-[{account_name}] Пытаемся добавить @{username} в {self.chat_link}")

        try:
            # 1. Проверяем существование пользователя и получаем количество общих чатов
            try:
                full_user = await client(GetFullUserRequest(username))
                old_common_chats = full_user.full_user.common_chats_count
            except (ValueError, TypeError, UsernameInvalidError, UsernameNotOccupiedError):
                logger.warning(
                    f"[{self.profile_name}]-[Worker-{worker_id}]-[{account_name}] Пользователь @{username} не существует")
                user.status = UserStatus.NOT_FOUND
                user.last_attempt = datetime.now()
                user.error_message = "Пользователь не найден"
                self.parent.processed_users[username] = user
                return False

            # 1.5 Проверяем общие чаты если есть ID текущего чата
            if self.chat_telegram_id and old_common_chats > 0:
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
                        if hasattr(chat, 'id') and chat.id == self.chat_telegram_id:
                            logger.warning(
                                f"👥 [{self.profile_name}]-[Worker-{worker_id}]-[{account_name}] @{username} уже в чате! (Чат: {self.chat_link})")
                            user.status = UserStatus.ALREADY_IN
                            user.last_attempt = datetime.now()
                            user.error_message = "Уже в чате"
                            self.parent.processed_users[username] = user
                            return False

                    logger.debug(
                        f"[{self.profile_name}]-[Worker-{worker_id}]-[{account_name}] @{username} не найден в текущем чате (Чат: {self.chat_link})")

                except Exception as e:
                    # Если не удалось проверить - продолжаем инвайт
                    logger.debug(
                        f"⚠[{self.profile_name}]-[Worker-{worker_id}]-[{account_name}] Не удалось проверить общие чаты: {e}")

            # 2. Пытаемся пригласить
            result = await client(InviteToChannelRequest(
                channel=self.chat_link,
                users=[username]
            ))

            # Проверяем есть ли missing_invitees (приватность)
            if result.missing_invitees:
                logger.warning(
                    f"[{self.profile_name}]-[Worker-{worker_id}]-[{account_name}] @{username} - настройки приватности (Чат: {self.chat_link})")
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
                logger.warning(
                    f"[{self.profile_name}]-[Worker-{worker_id}]-[{account_name}] @{username} добавлен и сразу списан (Чат: {self.chat_link})")
                user.status = UserStatus.ERROR
                user.last_attempt = datetime.now()
                user.error_message = "Списание"
                self.parent.processed_users[username] = user
                return False

            # Успешно добавлен
            logger.success(
                f"[{self.profile_name}]-[Worker-{worker_id}]-[{account_name}] @{username} успешно добавлен! (Чат: {self.chat_link})")
            user.status = UserStatus.INVITED
            user.last_attempt = datetime.now()
            self.parent.processed_users[username] = user
            return True

        except (PeerFloodError, FloodWaitError) as e:
            if isinstance(e, FloodWaitError):
                wait_seconds = e.seconds
                logger.warning(
                    f"[{self.profile_name}]-[Worker-{worker_id}]-[{account_name}] @{username} FloodWait: жду {wait_seconds} сек.")
                await asyncio.sleep(wait_seconds)
            else:
                logger.error(
                    f"[{self.profile_name}]-[Worker-{worker_id}]-[{account_name}] @{username} Спамблок при добавлении")

            user.status = UserStatus.SPAM_BLOCK
            user.last_attempt = datetime.now()
            user.error_message = str(e)
            self.parent.processed_users[username] = user
            return False

        except UserPrivacyRestrictedError:
            logger.warning(
                f"[{self.profile_name}]-[Worker-{worker_id}]-[{account_name}] @{username} - настройки приватности (Чат: {self.chat_link})")
            user.status = UserStatus.PRIVACY
            user.last_attempt = datetime.now()
            user.error_message = "Настройки приватности"
            self.parent.processed_users[username] = user
            return False

        except (UserDeactivatedBanError, UserDeactivatedError):
            logger.warning(
                f"[{self.profile_name}]-[Worker-{worker_id}]-[{account_name}] @{username} заблокирован в Telegram (Чат: {self.chat_link})")
            user.status = UserStatus.NOT_FOUND
            user.last_attempt = datetime.now()
            user.error_message = "Пользователь заблокирован"
            self.parent.processed_users[username] = user
            return False

        except (ChatAdminRequiredError, ChatWriteForbiddenError):
            logger.error(
                f"[{self.profile_name}]-[Worker-{worker_id}]-[{account_name}] Недостаточно прав в чате (Чат: {self.chat_link})")
            user.status = UserStatus.ERROR
            user.last_attempt = datetime.now()
            user.error_message = "Недостаточно прав в чате"
            self.parent.processed_users[username] = user
            return False

        except ChannelsTooMuchError:
            logger.warning(
                f"[{self.profile_name}]-[Worker-{worker_id}]-[{account_name}] @{username} уже в максимальном количестве чатов (Чат: {self.chat_link})")
            user.status = UserStatus.ERROR
            user.last_attempt = datetime.now()
            user.error_message = "Максимум чатов"
            self.parent.processed_users[username] = user
            return False

        except Exception as e:
            # Специфичные ошибки по тексту
            error_text = str(e)

            if "CHAT_MEMBER_ADD_FAILED" in error_text:
                logger.error(
                    f"[{self.profile_name}]-[Worker-{worker_id}]-[{account_name}] Не удалось добавить @{username} (Чат: {self.chat_link})")
                user.status = UserStatus.ERROR
                user.error_message = "Ошибка добавления"

            elif "You're banned from sending messages" in error_text:
                logger.error(
                    f"[{self.profile_name}]-[Worker-{worker_id}]-[{account_name}] Аккаунт заблокирован для инвайтов (Чат: {self.chat_link})")
                user.status = UserStatus.ERROR
                user.error_message = "Аккаунт заблокирован"

            elif "user was kicked" in error_text.lower():
                logger.warning(
                    f"[{self.profile_name}]-[Worker-{worker_id}]-[{account_name}] @{username} был ранее кикнут из чата (Чат: {self.chat_link})")
                user.status = UserStatus.ALREADY_IN
                user.error_message = "Был кикнут"

            elif "already in too many channels" in error_text.lower():
                logger.warning(
                    f"[{self.profile_name}]-[Worker-{worker_id}]-[{account_name}] @{username} в слишком многих чатах (Чат: {self.chat_link})")
                user.status = UserStatus.ERROR
                user.error_message = "Слишком много чатов"

            else:
                logger.error(
                    f"[{self.profile_name}]-[Worker-{worker_id}]-[{account_name}] Неизвестная ошибка для @{username}: {e} (Чат: {self.chat_link})")
                user.status = UserStatus.ERROR
                user.error_message = f"Ошибка: {error_text[:50]}"

            user.last_attempt = datetime.now()
            self.parent.processed_users[username] = user
            return False