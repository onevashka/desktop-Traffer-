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
                chat_links.append(chat)
                temp_queue.append(chat)

            # Возвращаем чаты обратно в очередь
            for chat in temp_queue:
                self.chat_queue.put(chat)

            if not chat_links:
                logger.error("❌ Нет чатов для обработки")
                return False

            # Выводим инструкции напрямую в лог
            logger.info(f"=" * 70)
            logger.info(f"🤖 ИНСТРУКЦИЯ ПО НАСТРОЙКЕ БОТА")
            logger.info(f"=" * 70)
            logger.info(f"1. Добавьте бота @{self.bot_manager.bot_username} в следующие чаты:")

            for i, chat in enumerate(chat_links, 1):
                logger.info(f"   {i}. {chat}")

            logger.info(f"2. Дайте боту права администратора во всех чатах")
            logger.info(f"3. После завершения настройки, работа продолжится автоматически")
            logger.info(f"=" * 70)

            # Даем пользователю время на настройку
            logger.info(f"⏳ Ожидаем 60 секунд для настройки...")
            await asyncio.sleep(60)

            logger.info(f"✅ Продолжаем работу")
            return True

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

        # Рассчитываем общее количество требуемых успешных инвайтов (как в классическом)
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
            logger.info(f"[{self.profile_name}] Лимит на аккаунт не установлен, используем {accounts_needed} аккаунтов")

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

        # Получаем аккаунты
        module_name = f"admin_inviter_{self.profile_name}"
        allocated_accounts = self._get_fresh_accounts(module_name, initial_accounts_to_request)

        if not allocated_accounts:
            logger.error(f"[{self.profile_name}] Не удалось получить свободные аккаунты")
            return

        logger.info(f"[{self.profile_name}] Получено аккаунтов на старте: {len(allocated_accounts)}")

        # Создаем потоки для чатов
        chat_index = 0
        account_index = 0

        while self.chat_queue.qsize() > 0 and not self.stop_flag.is_set():
            try:
                chat = self.chat_queue.get_nowait()

                # Проверяем есть ли аккаунты для этого чата
                if account_index >= len(allocated_accounts):
                    # Пробуем получить еще аккаунты
                    additional_accounts = self._get_fresh_accounts(
                        module_name,
                        self.config.threads_per_chat
                    )

                    if additional_accounts:
                        allocated_accounts.extend(additional_accounts)
                        logger.info(
                            f"[{self.profile_name}] Получено дополнительно {len(additional_accounts)} аккаунтов")
                    else:
                        # Возвращаем чат обратно в очередь
                        self.chat_queue.put(chat)
                        logger.warning(f"[{self.profile_name}] Нет аккаунтов для чата {chat}, отложен")
                        break

                # Выделяем аккаунты для этого чата
                chat_accounts = []
                accounts_to_allocate = min(self.config.threads_per_chat, len(allocated_accounts) - account_index)

                for j in range(accounts_to_allocate):
                    if account_index < len(allocated_accounts):
                        chat_accounts.append(allocated_accounts[account_index])
                        account_index += 1

                if not chat_accounts:
                    # Возвращаем чат обратно
                    self.chat_queue.put(chat)
                    logger.warning(f"[{self.profile_name}]  Не удалось выделить аккаунты для чата {chat}")
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

            # Выводим промежуточную статистику
            free_accounts = self.account_manager.get_free_accounts_count()
            active_accounts = len(alive)
            finished_accounts = len(self.finished_accounts)

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

                # Помечаем аккаунт как отработанный на 24 часа
                self._mark_account_as_finished(account_name)

        if error:
            stats.errors += 1
            self.total_errors += 1
        if spam_block:
            stats.spam_blocks += 1
            stats.consecutive_spam += 1

            # Проверяем лимит спамблоков
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

            # Сохраняем время окончания работы
            self.account_finish_times[account_name] = finish_time

            # Формируем сообщение для лога
            next_available = finish_time + timedelta(hours=24)
            logger.info(f"📌 [{self.profile_name}] Аккаунт {account_name} помечен как отработанный")
            logger.info(f"   ⏰ Будет доступен: {next_available.strftime('%Y-%m-%d %H:%M:%S')}")

        except Exception as e:
            logger.error(f"❌ [{self.profile_name}] Ошибка пометки аккаунта {account_name} как отработанного: {e}")

    def _print_final_stats(self):
        """Выводит финальную статистику"""
        logger.info("=" * 60)
        logger.info(f"[{self.profile_name}]   📊 ИТОГОВАЯ СТАТИСТИКА:")
        logger.info(f"[{self.profile_name}]   Всего обработано: {self.total_processed}")
        logger.info(f"[{self.profile_name}]   Успешных инвайтов: {self.total_success}")
        logger.info(f"[{self.profile_name}]   Ошибок: {self.total_errors}")

        if self.total_processed > 0:
            success_rate = (self.total_success / self.total_processed) * 100
            logger.info(f"[{self.profile_name}]   Процент успеха: {success_rate:.1f}%")

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

        # Флаги остановки чата
        self.chat_stop_reason = None
        self.stop_all_workers = False

        # Информация о чате для проверки
        self.chat_entity = None
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
            if self.parent.stop_flag.is_set() or self.stop_all_workers:
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
        logger.info(
            f"[{self.profile_name}]-[AdminChat-{self.chat_link}] Итоговая статистика: обработано={self.chat_processed}, успешно={self.chat_success}, ошибок={self.chat_errors}")

    async def _work_with_admin_account(self, account_data):
        """Работа с аккаунтом как с администратором"""
        account_name = account_data.name
        account = account_data.account

        logger.info(
            f"[{self.profile_name}]-[AdminChat-{self.chat_link}] 👨‍💼 Начинаем работу админа: {account_name}")

        invites_count = 0
        errors_count = 0

        # Получаем информацию о себе для проверки
        try:
            me = await account.client.get_me()
            logger.info(
                f"[{self.profile_name}]-[AdminChat-{self.chat_link}] Подключен как {me.first_name} {me.last_name or ''} (@{me.username or 'no_username'})")
        except Exception as e:
            logger.error(
                f"[{self.profile_name}]-[AdminChat-{self.chat_link}] Ошибка получения информации об аккаунте: {e}")
            return

        # Присоединяемся к чату если нужно
        chat_entity = None
        try:
            # Получаем entity чата
            chat_entity = await account.client.get_entity(self.chat_link)
            if hasattr(chat_entity, 'id'):
                self.chat_telegram_id = chat_entity.id

            logger.info(
                f"[{self.profile_name}]-[AdminChat-{self.chat_link}] Успешно получили данные чата: {self.chat_link}")
        except Exception as e:
            logger.error(
                f"[{self.profile_name}]-[AdminChat-{self.chat_link}] ❌ Ошибка получения данных чата: {e}")
            return

        # Основной цикл инвайтинга
        while not self.parent.stop_flag.is_set() and not self.stop_all_workers:
            # ВАЖНО: Проверяем достиг ли аккаунт лимита
            account_stats = self.parent.account_stats.get(account_name)
            if account_stats and account_stats.status == 'finished':
                logger.info(
                    f"[{self.profile_name}]-[AdminChat-{self.chat_link}] Аккаунт достиг лимита, завершаем работу")
                break

            # Проверяем не заблокирован ли аккаунт за спам
            if account_stats and account_stats.status == 'spam_blocked':
                logger.error(
                    f"[{self.profile_name}]-[AdminChat-{self.chat_link}] Аккаунт заблокирован за спам, завершаем работу")
                break

            # Проверяем лимит успешных для чата
            if self.parent.config.success_per_chat > 0 and self.chat_success >= self.parent.config.success_per_chat:
                logger.success(
                    f"[{self.profile_name}]-[AdminChat-{self.chat_link}] Достигнут лимит успешных инвайтов: {self.chat_success}")
                self.stop_all_workers = True
                break

            # Проверяем лимит для аккаунта
            if self.parent.config.success_per_account > 0:
                if invites_count >= self.parent.config.success_per_account:
                    logger.info(
                        f"[{self.profile_name}]-[AdminChat-{self.chat_link}] Достигнут лимит инвайтов для аккаунта: {invites_count}")
                    break

            # Получаем пользователя
            try:
                user = self.parent.user_queue.get_nowait()
            except queue.Empty:
                logger.info(f"[{self.profile_name}]-[AdminChat-{self.chat_link}] Очередь пуста")
                break

            # Инвайтим пользователя
            success = await self._invite_user(user, account, account_name)

            if success:
                invites_count += 1
                self.chat_success += 1
            else:
                errors_count += 1
                self.chat_errors += 1

            self.chat_processed += 1

            # Обновляем статистику аккаунта (проверка лимитов происходит внутри)
            self.parent.update_account_stats(
                account_name,
                success=success,
                spam_block=(user.status == UserStatus.SPAM_BLOCK if hasattr(user, 'status') else False),
                error=(not success)
            )

            # Задержка между инвайтами
            if self.parent.config.delay_between > 0:
                await asyncio.sleep(self.parent.config.delay_between)

        logger.info(
            f"[{self.profile_name}]-[AdminChat-{self.chat_link}] Завершен. Инвайтов: {invites_count}, ошибок: {errors_count}")

    async def _invite_user(self, user: InviteUser, account, account_name: str) -> bool:
        """Инвайт пользователя через Telethon с проверками"""
        client = account.client

        if not client or not client.is_connected():
            logger.error(f"❌ [{self.profile_name}]-[AdminChat-{self.chat_link}] Клиент не подключен")
            return False

        username = user.username
        if username.startswith('@'):
            username = username[1:]

        logger.info(
            f"[{self.profile_name}]-[AdminChat-{self.chat_link}] Пытаемся добавить @{username} в {self.chat_link}")

        try:
            # 1. Проверяем существование пользователя и получаем количество общих чатов
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
                                f"👥 [{self.profile_name}]-[AdminChat-{self.chat_link}] @{username} уже в чате!")
                            user.status = UserStatus.ALREADY_IN
                            user.last_attempt = datetime.now()
                            user.error_message = "Уже в чате"
                            self.parent.processed_users[username] = user
                            return False

                    logger.debug(
                        f"[{self.profile_name}]-[AdminChat-{self.chat_link}] @{username} не найден в текущем чате")

                except Exception as e:
                    # Если не удалось проверить - продолжаем инвайт
                    logger.debug(
                        f"⚠[{self.profile_name}]-[AdminChat-{self.chat_link}] Не удалось проверить общие чаты: {e}")

            # 2. Пытаемся пригласить
            try:
                # Получаем entity пользователя
                user_entity = await client.get_entity(username)

                # Приглашаем пользователя
                result = await client(InviteToChannelRequest(
                    channel=self.chat_link,
                    users=[user_entity]
                ))

                # Проверяем есть ли missing_invitees (приватность)
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

            # 3. Ждем и проверяем действительно ли добавился
            await asyncio.sleep(10)  # Даем время на обработку (меньше чем в классическом, у нас же админ)

            full_user2 = await client(GetFullUserRequest(username))
            new_common_chats = full_user2.full_user.common_chats_count

            # Если количество общих чатов не увеличилось - списание
            if new_common_chats <= old_common_chats:
                logger.warning(
                    f"[{self.profile_name}]-[AdminChat-{self.chat_link}] @{username} добавлен и сразу списан")
                user.status = UserStatus.ERROR
                user.last_attempt = datetime.now()
                user.error_message = "Списание"
                self.parent.processed_users[username] = user
                return False

            # Успешно добавлен
            logger.success(
                f"[{self.profile_name}]-[AdminChat-{self.chat_link}] @{username} успешно добавлен!")
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

        except UserPrivacyRestrictedError:
            logger.warning(
                f"[{self.profile_name}]-[AdminChat-{self.chat_link}] @{username} - настройки приватности")
            user.status = UserStatus.PRIVACY
            user.last_attempt = datetime.now()
            user.error_message = "Настройки приватности"
            self.parent.processed_users[username] = user
            return False

        except (UserDeactivatedBanError, UserDeactivatedError):
            logger.warning(
                f"[{self.profile_name}]-[AdminChat-{self.chat_link}] @{username} заблокирован в Telegram")
            user.status = UserStatus.NOT_FOUND
            user.last_attempt = datetime.now()
            user.error_message = "Пользователь заблокирован"
            self.parent.processed_users[username] = user
            return False

        except (ChatAdminRequiredError, ChatWriteForbiddenError):
            logger.error(
                f"[{self.profile_name}]-[AdminChat-{self.chat_link}] Недостаточно прав в чате (даже с админкой!)")
            user.status = UserStatus.ERROR
            user.last_attempt = datetime.now()
            user.error_message = "Недостаточно прав в чате"
            self.parent.processed_users[username] = user

            # Останавливаем все воркеры для этого чата, т.к. проблема с правами
            self.chat_stop_reason = "Недостаточно прав бота в чате"
            self.stop_all_workers = True
            return False

        except ChannelsTooMuchError:
            logger.warning(
                f"[{self.profile_name}]-[AdminChat-{self.chat_link}] @{username} уже в максимальном количестве чатов")
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
                    f"[{self.profile_name}]-[AdminChat-{self.chat_link}] Не удалось добавить @{username}")
                user.status = UserStatus.ERROR
                user.error_message = "Ошибка добавления"

            elif "You're banned from sending messages" in error_text:
                logger.error(
                    f"[{self.profile_name}]-[AdminChat-{self.chat_link}] Аккаунт заблокирован для инвайтов")
                user.status = UserStatus.ERROR
                user.error_message = "Аккаунт заблокирован"

            elif "user was kicked" in error_text.lower():
                logger.warning(
                    f"[{self.profile_name}]-[AdminChat-{self.chat_link}] @{username} был ранее кикнут из чата")
                user.status = UserStatus.ALREADY_IN
                user.error_message = "Был кикнут"

            elif "already in too many channels" in error_text.lower():
                logger.warning(
                    f"[{self.profile_name}]-[AdminChat-{self.chat_link}] @{username} в слишком многих чатах")
                user.status = UserStatus.ERROR
                user.error_message = "Слишком много чатов"

            else:
                logger.error(
                    f"[{self.profile_name}]-[AdminChat-{self.chat_link}] Неизвестная ошибка для @{username}: {e}")
                user.status = UserStatus.ERROR
                user.error_message = f"Ошибка: {error_text[:50]}"

            user.last_attempt = datetime.now()
            self.parent.processed_users[username] = user
            return False