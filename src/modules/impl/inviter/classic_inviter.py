# src/modules/impl/inviter/classic_inviter.py
"""
Классический режим инвайтинга - полноценная версия с автозаменой аккаунтов
"""

import threading
import asyncio
import queue
from typing import Dict, List
from datetime import datetime, timedelta
from loguru import logger

from .base_inviter import BaseInviterProcess
from src.entities.moduls.inviter import InviteUser, UserStatus, AccountStats

# Импорты Telethon
from telethon.tl.functions.channels import InviteToChannelRequest, JoinChannelRequest
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


class ClassicInviterProcess(BaseInviterProcess):
    """Классический инвайтер - один поток на чат с автозаменой аккаунтов"""

    def __init__(self, profile_name: str, profile_data: Dict, account_manager):
        super().__init__(profile_name, profile_data, account_manager)
        self.chat_threads = []

        # Статистика по аккаунтам
        self.account_stats: Dict[str, AccountStats] = {}

        # Общая статистика процесса
        self.total_success = 0
        self.total_errors = 0
        self.total_processed = 0

        # Множество замороженных аккаунтов
        self.frozen_accounts = set()

        # Множество отработанных аккаунтов (достигли лимита)
        self.finished_accounts = set()

        # Словарь с временем окончания работы аккаунтов (для 24-часовой метки)
        self.account_finish_times: Dict[str, datetime] = {}

        # Сохраняем начальное количество чатов для расчета прогресса
        self.initial_chats_count = 0

    def _run_inviting(self):
        """Запускает классический инвайтинг"""
        logger.info(f"[{self.profile_name}] Запуск классического инвайтинга")

        # Задержка после старта
        if self.config.delay_after_start > 0:
            logger.info(f"[{self.profile_name}] Задержка {self.config.delay_after_start} сек...")
            self.stop_flag.wait(self.config.delay_after_start)

        # Получаем начальное количество чатов
        total_chats = self.chat_queue.qsize()
        self.initial_chats_count = total_chats  # Сохраняем для расчета прогресса
        logger.info(f"[{self.profile_name}] Всего чатов для обработки: {total_chats}")

        # НОВАЯ ЛОГИКА РАСЧЕТА АККАУНТОВ
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

        # Получаем начальные аккаунты
        module_name = f"inviter_{self.profile_name}"
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
                thread = ChatWorkerThread(
                    chat_id=chat_index + 1,
                    chat_link=chat,
                    accounts=chat_accounts,
                    parent=self,
                    profile_name=self.profile_name
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
        """Получает только свежие (не отработанные) аккаунты"""
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

            # Выводим промежуточную статистику
            free_accounts = self.account_manager.get_free_accounts_count()
            active_accounts = len(alive)
            finished_accounts = len(self.finished_accounts)

            #logger.info(
                #f"[{self.profile_name}] Статус: потоков={active_accounts}, свободных аккаунтов={free_accounts}, отработало={finished_accounts}")

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

            # TODO: В будущем здесь будет сохранение в базу данных
            # self.account_manager.mark_account_finished(account_name, finish_time)

            # TODO: В будущем здесь будет перемещение в специальную папку
            # self.account_manager.move_to_finished_folder(account_name)

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


class ChatWorkerThread(threading.Thread):
    """Рабочий поток для одного чата с автоматической заменой аккаунтов"""

    def __init__(self, chat_id: int, chat_link: str, accounts: List, parent: ClassicInviterProcess, profile_name: str):
        super().__init__(name=f"Chat-{chat_id}")
        self.chat_id = chat_id
        self.chat_link = chat_link
        self.accounts = accounts  # Аккаунты выделенные для этого чата
        self.parent = parent
        self.main_loop = None  # Ссылка на основной event loop
        self.profile_name = profile_name

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

            # Сохраняем ссылку на loop для использования в воркерах
            self.main_loop = loop

            # Запускаем работу
            loop.run_until_complete(self._work())

        except Exception as e:
            logger.error(f"❌ [{self.profile_name}]-[Chat-{self.chat_id}] Ошибка: {e}")
        finally:
            loop.close()

    async def _work(self):
        """Основная работа с чатом - с автоматической заменой аккаунтов"""
        logger.info(f"[{self.profile_name}]-[Чат-{self.chat_link}] Начинаем работу")
        logger.info(f"[{self.profile_name}]-[Чат-{self.chat_link}] Доступно аккаунтов: {len(self.accounts)}")

        # Флаг завершения работы чата
        chat_completed = False

        # Счетчик активных воркеров для этого чата
        active_workers = []
        active_workers_lock = threading.Lock()

        # Предварительно создаем клиенты в текущем event loop
        logger.info(f"[{self.profile_name}]-[Чат-{self.chat_link}] Инициализируем клиенты...")
        for account_data in self.accounts:
            try:
                await account_data.account.create_client()
            except Exception as e:
                logger.error(f"[{self.profile_name}] Ошибка создания клиента для {account_data.name}: {e}")

        # Пока не завершена работа с чатом
        while not chat_completed and not self.parent.stop_flag.is_set():
            # Запускаем воркеров в отдельных потоках
            worker_threads = []

            for i, account_data in enumerate(self.accounts):
                # Проверяем не отработан ли уже аккаунт
                if account_data.name in self.parent.finished_accounts:
                    logger.info(
                        f"[{self.profile_name}]-[Чат-{self.chat_link}] Аккаунт {account_data.name} уже отработан, пропускаем")
                    continue

                # Создаем поток для каждого аккаунта
                worker_thread = threading.Thread(
                    target=self._run_worker_in_thread,
                    args=(i + 1, account_data, active_workers, active_workers_lock),
                    name=f"Чат-{self.chat_link}-Worker-{i + 1}"
                )
                worker_thread.start()
                worker_threads.append(worker_thread)

            logger.info(
                f"[{self.profile_name}]-[Чат-{self.chat_link}] Запущено {len(worker_threads)} потоков воркеров")

            # Проверяем статус периодически
            while not self.parent.stop_flag.is_set():
                # Ждем немного
                await asyncio.sleep(2)

                # Проверяем флаг остановки чата
                if self.stop_all_workers:
                    logger.warning(
                        f"[{self.profile_name}]-[Чат-{self.chat_link}] Остановка всех воркеров. Причина: {self.chat_stop_reason}")
                    chat_completed = True
                    break

                # Проверяем сколько воркеров еще работает
                with active_workers_lock:
                    still_working = len(active_workers)

                if still_working == 0:
                    logger.info(f"[{self.profile_name}]-[Чат-{self.chat_link}] Все воркеры завершили работу")
                    break

                # Проверяем условия завершения
                if self.parent.config.success_per_chat > 0 and self.chat_success >= self.parent.config.success_per_chat:
                    logger.success(
                        f"[{self.profile_name}]-[Чат-{self.chat_link}] Достигнут лимит успешных инвайтов: {self.chat_success}")
                    chat_completed = True
                    break

                if self.parent.user_queue.empty():
                    logger.info(f"[{self.profile_name}]-[Чат-{self.chat_link}] Закончились пользователи для инвайта")
                    # Даем воркерам доработать текущих пользователей
                    await asyncio.sleep(5)
                    chat_completed = True
                    break

            # Освобождаем аккаунты которые закончили работу
            module_name = f"inviter_{self.parent.profile_name}"
            released_count = 0

            for account_data in self.accounts:
                # Проверяем не работает ли еще этот аккаунт
                account_working = False
                with active_workers_lock:
                    account_working = account_data.name in active_workers

                if not account_working:
                    self.parent.account_manager.release_account(account_data.name, module_name)
                    released_count += 1

            logger.info(
                f"[{self.profile_name}]-[Чат-{self.chat_link}] Освобождено завершивших работу аккаунтов: {released_count}")

            # Проверяем нужно ли продолжать работу
            if chat_completed:
                break

            # Проверяем специальные случаи остановки чата
            if self.stop_all_workers:
                logger.warning(
                    f"[{self.profile_name}]-[Чат-{self.chat_link}] Чат остановлен. Причина: {self.chat_stop_reason}")
                break

            # Если есть пользователи и работа не завершена - запрашиваем новые аккаунты
            if not self.parent.user_queue.empty():
                logger.info(
                    f"[{self.profile_name}]-[Чат-{self.chat_link}] Запрашиваем новые аккаунты для продолжения работы")

                # Фильтруем отработанные аккаунты
                available_count = self.parent.account_manager.get_free_accounts_count()
                finished_count = len(self.parent.finished_accounts)

                logger.info(
                    f"[{self.profile_name}]-[Чат-{self.chat_link}] Доступно аккаунтов: {available_count}, отработано: {finished_count}")

                # Получаем новые аккаунты через метод с фильтрацией
                new_accounts = self.parent._get_fresh_accounts(
                    module_name,
                    self.parent.config.threads_per_chat
                )

                if not new_accounts:
                    logger.warning(
                        f"[{self.profile_name}]-[Чат-{self.chat_link}] Нет свободных неотработанных аккаунтов")
                    chat_completed = True
                    break

                # Инициализируем клиенты для новых аккаунтов
                logger.info(
                    f"[{self.profile_name}]-[Чат-{self.chat_link}] Инициализируем клиенты для новых аккаунтов...")
                for account_data in new_accounts:
                    try:
                        await account_data.account.create_client()
                    except Exception as e:
                        logger.error(f"Ошибка создания клиента для {account_data.name}: {e}")

                self.accounts = new_accounts
                logger.info(
                    f"[{self.profile_name}]-[Чат-{self.chat_link}] Получено новых активных аккаунтов: {len(new_accounts)}")

        # Финальная очистка - ждем оставшиеся воркеры
        logger.info(f"🧹 [{self.profile_name}]-[Чат-{self.chat_link}] Ожидаем завершения оставшихся воркеров...")

        # Даем воркерам время завершиться
        await asyncio.sleep(5)

        # Освобождаем все оставшиеся аккаунты
        module_name = f"inviter_{self.parent.profile_name}"
        for account_data in self.accounts:
            self.parent.account_manager.release_account(account_data.name, module_name)

        logger.info(f"[{self.profile_name}]-[Чат-{self.chat_link}] Работа завершена")
        logger.info(
            f"[{self.profile_name}]-[Чат-{self.chat_link}] Итоговая статистика: обработано={self.chat_processed}, успешно={self.chat_success}, ошибок={self.chat_errors}")

    def _run_worker_in_thread(self, worker_id: int, account_data, active_workers: list, lock: threading.Lock):
        """Обертка для запуска воркера в отдельном потоке"""
        # Добавляем себя в список активных
        with lock:
            active_workers.append(account_data.name)

        try:
            # Используем loop из ChatWorkerThread
            chat_loop = self.main_loop

            # Запускаем корутину в loop чата из другого потока
            future = asyncio.run_coroutine_threadsafe(
                self._run_worker(worker_id, account_data),
                chat_loop
            )

            # Ждем завершения
            future.result()

        except Exception as e:
            logger.error(f"[{self.profile_name}]-[Поток-{worker_id}] Ошибка в потоке: {e}")
        finally:
            # Удаляем себя из списка активных
            with lock:
                if account_data.name in active_workers:
                    active_workers.remove(account_data.name)

            # Освобождаем аккаунт через loop чата
            try:
                module_name = f"inviter_{self.parent.profile_name}"
                asyncio.run_coroutine_threadsafe(
                    self._release_account_async(account_data.name, module_name),
                    chat_loop
                ).result(timeout=5)
            except Exception as e:
                logger.error(
                    f"[{self.profile_name}]-[Поток-{worker_id}] Ошибка освобождения аккаунта {account_data.name}: {e}")

    async def _release_account_async(self, account_name: str, module_name: str):
        """Асинхронное освобождение аккаунта"""
        self.parent.account_manager.release_account(account_name, module_name)
        logger.info(f"Аккаунт {account_name} освобожден")

    async def _run_worker(self, worker_id: int, account_data):
        """Воркер для инвайтинга с проверкой лимитов"""
        account_name = account_data.name
        account = account_data.account

        logger.info(
            f"[{self.profile_name}]-[Чат-{self.chat_link}]-[Поток-{worker_id}] Запуск с аккаунтом {account_name}")

        try:
            # Клиент уже должен быть создан в основном потоке
            if not account.client:
                logger.error(
                    f"[{self.profile_name}]-[Поток-{worker_id}]-[{account.name}] Клиент не создан для {account_name}")
                return

            # Подключаемся
            if not await account.connect():
                logger.error(
                    f"[{self.profile_name}]-[Поток-{worker_id}]-[{account.name}] Не удалось подключить {account_name}")
                return

            # Проверяем авторизацию
            if not await account.client.is_user_authorized():
                logger.error(
                    f"[{self.profile_name}]-[Поток-{worker_id}]-[{account.name}] Аккаунт {account_name} не авторизован")
                await account.disconnect()
                return

            # Получаем информацию о себе для проверки
            try:
                me = await account.client.get_me()
                logger.info(
                    f"[{self.profile_name}]-[Поток-{worker_id}]-[{account.name}] Подключен как {me.first_name} {me.last_name or ''} (@{me.username or 'no_username'})")
            except Exception as e:
                logger.error(
                    f"[{self.profile_name}]-[Поток-{worker_id}]-[{account.name}] Ошибка получения информации об аккаунте: {e}")
                await account.disconnect()
                return

            # Присоединяемся к чату
            join_result = await self._join_chat(account, worker_id)

            # Обрабатываем результат присоединения
            if join_result == "STOP_CHAT":
                logger.warning(
                    f"[{self.profile_name}]-[Поток-{worker_id}]-[{account.name}] Остановка всех воркеров чата. Причина: {self.chat_stop_reason}")
                self.stop_all_workers = True
                await account.disconnect()
                return
            elif join_result == "FROZEN_ACCOUNT":
                logger.error(
                    f"[{self.profile_name}]-[Поток-{worker_id}]-[{account.name}] Аккаунт заморожен, завершаем работу")
                await account.disconnect()
                return
            elif join_result != "SUCCESS":
                logger.error(
                    f"[{self.profile_name}]-[Поток-{worker_id}]-[{account.name}] Не удалось присоединиться к чату")
                await account.disconnect()
                return

            invites_count = 0
            errors_count = 0

            # Основной цикл инвайтинга
            while not self.parent.stop_flag.is_set() and not self.stop_all_workers:
                # ВАЖНО: Проверяем достиг ли аккаунт лимита
                account_stats = self.parent.account_stats.get(account_name)
                if account_stats and account_stats.status == 'finished':
                    logger.info(
                        f"[{self.profile_name}]-[Поток-{worker_id}]-[{account.name}] Аккаунт достиг лимита, завершаем работу")
                    break

                # Проверяем не заблокирован ли аккаунт за спам
                if account_stats and account_stats.status == 'spam_blocked':
                    logger.error(
                        f"[{self.profile_name}]-[Поток-{worker_id}]-[{account.name}] Аккаунт заблокирован за спам, завершаем работу")
                    break

                # Проверяем лимит успешных для чата
                if self.parent.config.success_per_chat > 0:
                    if self.chat_success >= self.parent.config.success_per_chat:
                        logger.info(
                            f"[{self.profile_name}]-[Чат-{self.chat_link}] Достигнут лимит успешных инвайтов для чата: {self.chat_success}")
                        break

                # Проверяем лимит для аккаунта
                if self.parent.config.success_per_account > 0:
                    if invites_count >= self.parent.config.success_per_account:
                        logger.info(
                            f"[{self.profile_name}]-[Поток-{worker_id}] Достигнут лимит инвайтов для аккаунта: {invites_count}")
                        break

                # Получаем пользователя
                try:
                    user = self.parent.user_queue.get_nowait()
                except queue.Empty:
                    logger.info(f"[{self.profile_name}]-[Поток-{worker_id}] Очередь пуста")
                    break

                # Инвайтим пользователя
                success = await self._invite_user(user, account, account_name, worker_id)

                if success:
                    invites_count += 1
                    self.chat_success += 1
                else:
                    errors_count += 1

                self.chat_processed += 1

                # Обновляем статистику аккаунта (проверка лимитов происходит внутри)
                self.parent.update_account_stats(
                    account_name,
                    success=success,
                    spam_block=(user.status == UserStatus.SPAM_BLOCK),
                    error=(not success)
                )

                # Задержка между инвайтами
                if self.parent.config.delay_between > 0:
                    await asyncio.sleep(self.parent.config.delay_between)

            logger.info(
                f"[{self.profile_name}]-[Поток-{worker_id}] Завершен. Инвайтов: {invites_count}, ошибок: {errors_count}")

        except Exception as e:
            logger.error(f"[{self.profile_name}]-[Поток-{worker_id}] Критическая ошибка: {e}")
        finally:
            # Отключаемся от Telegram
            try:
                await account.disconnect()
                await asyncio.sleep(30)
            except:
                pass

    async def _join_chat(self, account, worker_id: int) -> str:
        """Присоединяется к чату"""
        try:
            result = await account.join(self.chat_link)

            # Анализируем результат
            if result == "ALREADY_PARTICIPANT":
                logger.info(
                    f"[{self.profile_name}]-[Поток-{worker_id}]-[{account.name}] Уже в чате {self.chat_link}")
                return "SUCCESS"

            elif result == "FROZEN_ACCOUNT":
                logger.error(f"[{self.profile_name}]-[Поток-{worker_id}]-[{account.name}] Аккаунт заморожен")
                return "FROZEN_ACCOUNT"

            elif result == "CHAT_NOT_FOUND":
                logger.error(
                    f"[{self.profile_name}]-[Поток-{worker_id}]-[{account.name}] Чат не найден: {self.chat_link}")
                self.chat_stop_reason = "Чат не найден"
                return "STOP_CHAT"

            elif result == "REQUEST_SENT":
                logger.warning(
                    f"[{self.profile_name}]-[Поток-{worker_id}]-[{account.name}] Отправлен запрос на вступление в {self.chat_link}")
                return False

            elif result == "FLOOD_WAIT":
                logger.warning(
                    f"[{self.profile_name}]-[Поток-{worker_id}]-[{account.name}] Нужно подождать перед присоединением в {self.chat_link}")
                return False

            elif isinstance(result, str) and result.startswith("ERROR:"):
                logger.error(f"❌ [{self.profile_name}]-[Поток-{worker_id}] Ошибка: {result}")
                return False

            else:
                # Успешно присоединились
                logger.info(
                    f"[{self.profile_name}]-[Поток-{worker_id}]-[{account.name}] Присоединился к чату {self.chat_link}")

                # Сохраняем информацию о чате
                if hasattr(result, 'id'):
                    self.chat_telegram_id = result.id

                # Задержка после присоединения
                if self.parent.config.delay_after_start > 0:
                    await asyncio.sleep(self.parent.config.delay_after_start)

                return "SUCCESS"

        except Exception as e:
            logger.error(
                f"[{self.profile_name}]-[Поток-{worker_id}]-[{account.name}] Ошибка присоединения к чату {self.chat_link}: {e}")
            return False

    async def _invite_user(self, user: InviteUser, account, account_name: str, worker_id: int) -> bool:
        """Инвайт пользователя через Telethon"""
        client = account.client

        if not client or not client.is_connected():
            logger.error(f"❌ [{self.profile_name}]-[Поток-{worker_id}]-[{account.name}] Клиент не подключен")
            return False

        username = user.username
        if username.startswith('@'):
            username = username[1:]

        logger.info(
            f"[{self.profile_name}]-[Поток-{worker_id}]-[{account.name}] Пытаемся добавить @{username} в {self.chat_link}")

        try:
            # 1. Проверяем существование пользователя и получаем количество общих чатов
            try:
                full_user = await client(GetFullUserRequest(username))
                old_common_chats = full_user.full_user.common_chats_count
            except (ValueError, TypeError, UsernameInvalidError, UsernameNotOccupiedError):
                logger.warning(
                    f"[{self.profile_name}]-[Поток-{worker_id}]-[{account.name}] Пользователь @{username} не существует")
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
                                f"👥 [{self.profile_name}]-[Поток-{worker_id}]-[{account.name}] @{username} уже в чате! (Чат: {self.chat_link})")
                            user.status = UserStatus.ALREADY_IN
                            user.last_attempt = datetime.now()
                            user.error_message = "Уже в чате"
                            self.parent.processed_users[username] = user
                            return False

                    logger.debug(
                        f"[{self.profile_name}]-[Поток-{worker_id}]-[{account.name}] @{username} не найден в текущем чате (Чат: {self.chat_link})")

                except Exception as e:
                    # Если не удалось проверить - продолжаем инвайт
                    logger.debug(
                        f"⚠[{self.profile_name}]-[Поток-{worker_id}]-[{account.name}] Не удалось проверить общие чаты: {e}")

            # 2. Пытаемся пригласить
            result = await client(InviteToChannelRequest(
                channel=self.chat_link,
                users=[username]
            ))

            # Проверяем есть ли missing_invitees (приватность)
            if result.missing_invitees:
                logger.warning(
                    f"[{self.profile_name}]-[Поток-{worker_id}]-[{account.name}] @{username} - настройки приватности (Чат: {self.chat_link})")
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
                    f"[{self.profile_name}]-[Поток-{worker_id}]-[{account.name}] @{username} добавлен и сразу списан (Чат: {self.chat_link})")
                user.status = UserStatus.ERROR
                user.last_attempt = datetime.now()
                user.error_message = "Списание"
                self.parent.processed_users[username] = user
                return False

            # Успешно добавлен
            logger.success(
                f"[{self.profile_name}]-[Поток-{worker_id}]-[{account.name}] @{username} успешно добавлен! (Чат: {self.chat_link})")
            user.status = UserStatus.INVITED
            user.last_attempt = datetime.now()
            self.parent.processed_users[username] = user
            return True


        except (PeerFloodError, FloodWaitError) as e:
            print("Поля __dict__:", e.__dict__)
            if isinstance(e, FloodWaitError):
                wait_seconds = e.seconds
                logger.warning(f"[{self.profile_name}]-[Поток-{worker_id}]-[{account.name}] @{username}  FloodWait: жду {wait_seconds} сек.")
                await asyncio.sleep(wait_seconds)
            else:
                logger.error(f"[{self.profile_name}]-[Поток-{worker_id}]-[{account.name}] @{username} Спамблок при добавлении @{username}")
            # общая логика «отложить/пропустить этот user»
            user.status = UserStatus.SPAM_BLOCK
            user.last_attempt = datetime.now()
            user.error_message = str(e)
            self.parent.processed_users[username] = user
            return False

        except UserPrivacyRestrictedError:
            logger.warning(
                f"[{self.profile_name}]-[Поток-{worker_id}]-[{account.name}] @{username} - настройки приватности (Чат: {self.chat_link})")
            user.status = UserStatus.PRIVACY
            user.last_attempt = datetime.now()
            user.error_message = "Настройки приватности"
            self.parent.processed_users[username] = user
            return False

        except (UserDeactivatedBanError, UserDeactivatedError):
            logger.warning(
                f"[{self.profile_name}]-[Поток-{worker_id}]-[{account.name}] @{username} заблокирован в Telegram (Чат: {self.chat_link})")
            user.status = UserStatus.NOT_FOUND
            user.last_attempt = datetime.now()
            user.error_message = "Пользователь заблокирован"
            self.parent.processed_users[username] = user
            return False

        except (ChatAdminRequiredError, ChatWriteForbiddenError):
            logger.error(
                f"[{self.profile_name}]-[Поток-{worker_id}]-[{account.name}] Недостаточно прав в чате (Чат: {self.chat_link})")
            user.status = UserStatus.ERROR
            user.last_attempt = datetime.now()
            user.error_message = "Недостаточно прав в чате"
            self.parent.processed_users[username] = user
            return False

        except ChannelsTooMuchError:
            logger.warning(
                f"[{self.profile_name}]-[Поток-{worker_id}]-[{account.name}] @{username} уже в максимальном количестве чатов (Чат: {self.chat_link})")
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
                    f"[{self.profile_name}]-[Поток-{worker_id}]-[{account.name}] Не удалось добавить @{username} (Чат: {self.chat_link})")
                user.status = UserStatus.ERROR
                user.error_message = "Ошибка добавления"

            elif "You're banned from sending messages" in error_text:
                logger.error(
                    f"[{self.profile_name}]-[Поток-{worker_id}]-[{account.name}] Аккаунт заблокирован для инвайтов (Чат: {self.chat_link})")
                user.status = UserStatus.ERROR
                user.error_message = "Аккаунт заблокирован"

            elif "user was kicked" in error_text.lower():
                logger.warning(
                    f"[{self.profile_name}]-[Поток-{worker_id}]-[{account.name}] @{username} был ранее кикнут из чата (Чат: {self.chat_link})")
                user.status = UserStatus.ALREADY_IN
                user.error_message = "Был кикнут"

            elif "already in too many channels" in error_text.lower():
                logger.warning(
                    f"[{self.profile_name}]-[Поток-{worker_id}]-[{account.name}] @{username} в слишком многих чатах (Чат: {self.chat_link})")
                user.status = UserStatus.ERROR
                user.error_message = "Слишком много чатов"

            else:
                logger.error(
                    f"[{self.profile_name}]-[Поток-{worker_id}]-[{account.name}] Неизвестная ошибка для @{username}: {e} (Чат: {self.chat_link})")
                user.status = UserStatus.ERROR
                user.error_message = f"Ошибка: {error_text[:50]}"

            user.last_attempt = datetime.now()
            self.parent.processed_users[username] = user
            return False