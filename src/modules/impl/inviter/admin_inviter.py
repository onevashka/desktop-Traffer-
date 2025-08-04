# src/modules/impl/inviter/admin_inviter.py
"""
Инвайтер через админку - использует бота для управления правами админов
"""

import threading
import asyncio
import queue
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from loguru import logger

from .base_inviter import BaseInviterProcess
from .bot_manager import BotManager
from .admin_rights_manager import AdminRightsManager
from src.entities.moduls.inviter import InviteUser, UserStatus, AccountStats

# Импорты Telethon для инвайтов
from telethon.tl.functions.channels import InviteToChannelRequest
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

        # Информация о боте
        self.bot_account_info = profile_data.get('config', {}).get('bot_account')
        if not self.bot_account_info:
            logger.error(f"❌ Не указан аккаунт для бота в профиле {profile_name}")

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
        if self.bot_account_info:
            logger.info(f"   Бот-аккаунт: {self.bot_account_info.get('name', 'Unknown')}")

    def _run_inviting(self):
        """Основная логика инвайтинга через админку"""
        logger.info(f"[{self.profile_name}] 🤖 Запуск инвайтинга через админку")

        if not self.bot_account_info:
            logger.error(f"[{self.profile_name}] ❌ Не настроен аккаунт для бота!")
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

            # 2. Взаимодействие с пользователем
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
                await self.bot_manager.close()

    async def _initialize_bot(self) -> bool:
        """Инициализирует бот-менеджер"""
        try:
            logger.info(f"[{self.profile_name}] 🤖 Инициализация бота...")

            # Создаем бот-менеджер
            self.bot_manager = BotManager(
                account_name=self.bot_account_info['name'],
                profile_name=self.profile_name
            )

            # Инициализируем бота
            if not await self.bot_manager.initialize():
                return False

            # Создаем менеджер админ-прав
            self.admin_rights_manager = AdminRightsManager(
                bot_manager=self.bot_manager,
                profile_name=self.profile_name
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
                chat_links.append(chat.link)
                temp_queue.append(chat)

            # Возвращаем чаты обратно в очередь
            for chat in temp_queue:
                self.chat_queue.put(chat)

            if not chat_links:
                logger.error("❌ Нет чатов для обработки")
                return False

            # Показываем инструкции пользователю
            from .console_interface import get_console_interface
            console = get_console_interface()

            return console.show_bot_setup_instructions(
                bot_username=self.bot_manager.bot_username,
                profile_name=self.profile_name,
                chat_links=chat_links
            )

        except Exception as e:
            logger.error(f"❌ Ошибка взаимодействия с пользователем: {e}")
            return False

    async def _start_chat_threads(self):
        """Запускает потоки для чатов (синхронная часть как в классическом)"""
        # Переключаемся на синхронную логику
        # Задержка после старта
        if self.config.delay_after_start > 0:
            logger.info(f"[{self.profile_name}] Задержка {self.config.delay_after_start} сек...")
            self.stop_flag.wait(self.config.delay_after_start)

        # Получаем начальное количество чатов
        total_chats = self.chat_queue.qsize()
        self.initial_chats_count = total_chats
        logger.info(f"[{self.profile_name}] Всего чатов для обработки: {total_chats}")

        # Рассчитываем количество аккаунтов (как в классическом)
        total_invites_needed = total_chats * self.config.success_per_chat if self.config.success_per_chat > 0 else 999999
        accounts_needed = min(
            total_invites_needed // 10 if total_invites_needed > 0 else 50,
            self.config.account_limit if self.config.account_limit > 0 else 999999
        )

        # Получаем аккаунты
        module_name = f"admin_inviter_{self.profile_name}"
        allocated_accounts = self._get_fresh_accounts(module_name, accounts_needed)

        if not allocated_accounts:
            logger.error(f"[{self.profile_name}] Не удалось получить свободные аккаунты")
            return

        logger.info(f"[{self.profile_name}] Получено аккаунтов: {len(allocated_accounts)}")

        # Создаем потоки для чатов
        chat_index = 0
        account_index = 0

        while self.chat_queue.qsize() > 0 and not self.stop_flag.is_set():
            try:
                chat = self.chat_queue.get_nowait()

                # Выделяем аккаунты для этого чата
                chat_accounts = []
                accounts_to_allocate = min(self.config.threads_per_chat, len(allocated_accounts) - account_index)

                for j in range(accounts_to_allocate):
                    if account_index < len(allocated_accounts):
                        chat_accounts.append(allocated_accounts[account_index])
                        account_index += 1

                if not chat_accounts:
                    self.chat_queue.put(chat)
                    logger.warning(f"[{self.profile_name}] Нет аккаунтов для чата {chat}")
                    break

                # Создаем поток для чата
                thread = AdminChatWorkerThread(
                    chat_id=chat_index + 1,
                    chat_link=chat,
                    accounts=chat_accounts,
                    parent=self,
                    profile_name=self.profile_name,
                    bot_manager=self.bot_manager,
                    admin_rights_manager=self.admin_rights_manager
                )
                thread.start()
                self.chat_threads.append(thread)
                chat_index += 1

                logger.info(
                    f"[{self.profile_name}] Запущен поток для чата #{chat_index}: {chat} (аккаунтов: {len(chat_accounts)})")

            except queue.Empty:
                break

        # Ждем завершения всех потоков
        self._wait_for_threads()
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
        """Ждет завершения всех потоков (копия из классического)"""
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
        """Обновляет статистику аккаунта (копия из классического)"""
        if account_name not in self.account_stats:
            self.account_stats[account_name] = AccountStats(name=account_name)

        stats = self.account_stats[account_name]

        if success:
            stats.invites += 1
            self.total_success += 1

            if self.config.success_per_account > 0 and stats.invites >= self.config.success_per_account:
                stats.status = 'finished'
                self.finished_accounts.add(account_name)
                self.account_finish_times[account_name] = datetime.now()
                logger.warning(f"[{self.profile_name}] Аккаунт {account_name} достиг лимита инвайтов: {stats.invites}")

        if spam_block:
            stats.spam_blocks += 1
            stats.status = 'frozen'
            self.frozen_accounts.add(account_name)
            logger.error(f"[{self.profile_name}] Аккаунт {account_name} получил спамблок")

        if error:
            stats.errors += 1

        self.total_processed += 1

    def _print_final_stats(self):
        """Выводит итоговую статистику (копия из классического)"""
        logger.info("=" * 60)
        logger.info(f"📊 ИТОГОВАЯ СТАТИСТИКА АДМИН-ИНВАЙТЕРА: {self.profile_name}")
        logger.info("=" * 60)

        logger.info(f"🎯 ОБЩИЕ РЕЗУЛЬТАТЫ:")
        logger.info(f"   ✅ Успешных инвайтов: {self.total_success}")
        logger.info(f"   ❌ Ошибок: {self.total_errors}")
        logger.info(f"   📊 Всего обработано: {self.total_processed}")

        if self.account_stats:
            logger.info(f"\n👥 СТАТИСТИКА ПО АККАУНТАМ:")
            for account_name, stats in self.account_stats.items():
                status_icon = "🏁" if stats.status == 'finished' else "⚡" if stats.status == 'working' else "❌"
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
    """Рабочий поток для одного чата с управлением админ-правами"""

    def __init__(self, chat_id: int, chat_link: str, accounts: List, parent: AdminInviterProcess,
                 profile_name: str, bot_manager: BotManager, admin_rights_manager: AdminRightsManager):
        super().__init__(name=f"AdminChat-{chat_id}")
        self.chat_id = chat_id
        self.chat_link = chat_link
        self.accounts = accounts
        self.parent = parent
        self.profile_name = profile_name
        self.bot_manager = bot_manager
        self.admin_rights_manager = admin_rights_manager
        self.main_loop = None

        # Статистика чата
        self.chat_success = 0
        self.chat_errors = 0
        self.chat_processed = 0

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
            loop.close()

    async def _work(self):
        """Основная работа с чатом через админку"""
        logger.info(f"[{self.profile_name}]-[AdminChat-{self.chat_link}] 🤖 Начинаем работу через админку")
        logger.info(f"[{self.profile_name}]-[AdminChat-{self.chat_link}] Доступно аккаунтов: {len(self.accounts)}")

        # Предварительно создаем клиенты
        logger.info(f"[{self.profile_name}]-[AdminChat-{self.chat_link}] Инициализируем клиенты...")
        for account_data in self.accounts:
            try:
                await account_data.account.create_client()
            except Exception as e:
                logger.error(f"[{self.profile_name}] Ошибка создания клиента для {account_data.name}: {e}")

        # Основной цикл работы - один аккаунт за раз
        for account_data in self.accounts:
            if self.parent.stop_flag.is_set():
                break

            if account_data.name in self.parent.finished_accounts:
                logger.info(
                    f"[{self.profile_name}]-[AdminChat-{self.chat_link}] Аккаунт {account_data.name} уже отработан, пропускаем")
                continue

            try:
                # 1. ВЫДАЕМ ПРАВА АДМИНА аккаунту
                logger.info(
                    f"[{self.profile_name}]-[AdminChat-{self.chat_link}] 🔧 Выдаем права админа: {account_data.name}")

                admin_granted = await self.admin_rights_manager.grant_admin_rights(
                    account=account_data.account,
                    chat_link=self.chat_link
                )

                if not admin_granted:
                    logger.error(
                        f"[{self.profile_name}]-[AdminChat-{self.chat_link}] ❌ Не удалось выдать права админа: {account_data.name}")
                    continue

                logger.info(
                    f"[{self.profile_name}]-[AdminChat-{self.chat_link}] ✅ Права админа выданы: {account_data.name}")

                # 2. РАБОТАЕМ с аккаунтом как админом
                await self._work_with_admin_account(account_data)

            except Exception as e:
                logger.error(
                    f"[{self.profile_name}]-[AdminChat-{self.chat_link}] ❌ Ошибка работы с аккаунтом {account_data.name}: {e}")
            finally:
                # 3. ЗАБИРАЕМ ПРАВА АДМИНА (всегда!)
                try:
                    logger.info(
                        f"[{self.profile_name}]-[AdminChat-{self.chat_link}] 🔄 Забираем права админа: {account_data.name}")

                    await self.admin_rights_manager.revoke_admin_rights(
                        account=account_data.account,
                        chat_link=self.chat_link
                    )

                    logger.info(
                        f"[{self.profile_name}]-[AdminChat-{self.chat_link}] ✅ Права админа отозваны: {account_data.name}")

                except Exception as e:
                    logger.error(
                        f"[{self.profile_name}]-[AdminChat-{self.chat_link}] ❌ Ошибка отзыва прав: {account_data.name}: {e}")

        logger.info(f"[{self.profile_name}]-[AdminChat-{self.chat_link}] 🏁 Работа с чатом завершена")

    async def _work_with_admin_account(self, account_data):
        """Работа с аккаунтом как с администратором"""
        account_success = 0
        account_errors = 0
        consecutive_errors = 0

        logger.info(
            f"[{self.profile_name}]-[AdminChat-{self.chat_link}] 👨‍💼 Начинаем работу админа: {account_data.name}")

        while not self.parent.stop_flag.is_set():
            # Проверяем лимиты
            if self.parent.config.success_per_account > 0 and account_success >= self.parent.config.success_per_account:
                logger.info(
                    f"[{self.profile_name}]-[AdminChat-{self.chat_link}] 🎯 Аккаунт {account_data.name} достиг лимита: {account_success}")
                break

            if consecutive_errors >= self.parent.config.spam_errors:
                logger.warning(
                    f"[{self.profile_name}]-[AdminChat-{self.chat_link}] ⚠️ Много ошибок подряд для {account_data.name}: {consecutive_errors}")
                break

            # Получаем пользователя для инвайта
            try:
                user = self.parent.user_queue.get_nowait()
            except queue.Empty:
                logger.info(
                    f"[{self.profile_name}]-[AdminChat-{self.chat_link}] 📭 Закончились пользователи для {account_data.name}")
                break

            # Инвайтим пользователя (стандартная логика как в классическом)
            try:
                success = await self._invite_user_as_admin(account_data.account, user)

                if success:
                    account_success += 1
                    self.chat_success += 1
                    consecutive_errors = 0
                    self.parent.update_account_stats(account_data.name, success=True)
                    logger.debug(
                        f"[{self.profile_name}]-[AdminChat-{self.chat_link}] ✅ Инвайт: {account_data.name} → @{user.username}")
                else:
                    account_errors += 1
                    self.chat_errors += 1
                    consecutive_errors += 1
                    self.parent.update_account_stats(account_data.name, error=True)

                # Задержка между инвайтами
                if self.parent.config.invite_delay > 0:
                    await asyncio.sleep(self.parent.config.invite_delay)

            except Exception as e:
                account_errors += 1
                self.chat_errors += 1
                consecutive_errors += 1
                self.parent.update_account_stats(account_data.name, error=True)
                logger.error(
                    f"[{self.profile_name}]-[AdminChat-{self.chat_link}] ❌ Ошибка инвайта {account_data.name}: {e}")

        logger.info(
            f"[{self.profile_name}]-[AdminChat-{self.chat_link}] 📊 Аккаунт {account_data.name} завершил работу: успехов={account_success}, ошибок={account_errors}")

    async def _invite_user_as_admin(self, account, user: InviteUser) -> bool:
        """Инвайтит пользователя как администратор (стандартная логика)"""
        try:
            # Получаем entity чата и пользователя
            chat_entity = await account.client.get_input_entity(self.chat_link)
            user_entity = await account.client.get_input_entity(user.username)

            # Инвайтим через MTProto (как в классическом)
            await account.client(InviteToChannelRequest(
                channel=chat_entity,
                users=[user_entity]
            ))

            return True

        except UserPrivacyRestrictedError:
            logger.debug(f"[{self.profile_name}] 🔒 Пользователь @{user.username} запретил добавления")
            return False
        except FloodWaitError as e:
            logger.warning(f"[{self.profile_name}] ⏳ Флуд-лимит для {account.name}: {e.seconds} сек")
            await asyncio.sleep(e.seconds)
            return False
        except PeerFloodError:
            logger.error(f"[{self.profile_name}] 🚫 Спамблок для {account.name}")
            self.parent.update_account_stats(account.name, spam_block=True)
            return False
        except Exception as e:
            logger.error(f"[{self.profile_name}] ❌ Ошибка инвайта @{user.username}: {e}")
            return False