# src/modules/impl/inviter/classic_inviter.py
"""
Классический режим инвайтинга - полноценная версия
"""

import threading
import asyncio
import queue
from typing import Dict, List
from datetime import datetime
from loguru import logger

from .base_inviter import BaseInviterProcess
from src.entities.moduls.inviter import InviteUser, UserStatus, AccountStats

# Импорты Telethon
from telethon.tl.functions.channels import InviteToChannelRequest, JoinChannelRequest
from telethon.tl.functions.users import GetFullUserRequest
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
    """Классический инвайтер - один поток на чат"""

    def __init__(self, profile_name: str, profile_data: Dict, account_manager):
        super().__init__(profile_name, profile_data, account_manager)
        self.chat_threads = []

        # Статистика по аккаунтам
        self.account_stats: Dict[str, AccountStats] = {}

        # Общая статистика процесса
        self.total_success = 0
        self.total_errors = 0
        self.total_processed = 0

    def _run_inviting(self):
        """Запускает классический инвайтинг"""
        logger.info("🚀 Запуск классического инвайтинга")

        # Задержка после старта
        if self.config.delay_after_start > 0:
            logger.info(f"⏳ Задержка {self.config.delay_after_start} сек...")
            self.stop_flag.wait(self.config.delay_after_start)

        # Получаем начальное количество чатов
        total_chats = self.chat_queue.qsize()
        logger.info(f"💬 Всего чатов для обработки: {total_chats}")

        # НОВАЯ ЛОГИКА РАСЧЕТА АККАУНТОВ
        # Рассчитываем общее количество требуемых успешных инвайтов
        total_invites_needed = total_chats * self.config.success_per_chat
        logger.info(f"📊 Требуется успешных инвайтов всего: {total_invites_needed}")

        # Рассчитываем сколько аккаунтов нужно исходя из лимита на аккаунт
        if self.config.success_per_account > 0:
            accounts_needed = (
                                          total_invites_needed + self.config.success_per_account - 1) // self.config.success_per_account
            logger.info(
                f"📊 Расчетное количество аккаунтов: {accounts_needed} (по {self.config.success_per_account} инвайтов с аккаунта)")
        else:
            # Если лимит не установлен, используем старую логику
            accounts_needed = total_chats * self.config.threads_per_chat
            logger.info(f"📊 Лимит на аккаунт не установлен, используем {accounts_needed} аккаунтов")

        # Проверяем доступность аккаунтов
        available_accounts = self.account_manager.get_free_accounts_count()
        logger.info(f"📊 Доступно свободных аккаунтов: {available_accounts}")

        # Определяем сколько аккаунтов запросить на старте
        initial_accounts_to_request = min(accounts_needed, available_accounts)

        if initial_accounts_to_request < accounts_needed:
            logger.warning(f"⚠️ Недостаточно аккаунтов! Требуется: {accounts_needed}, доступно: {available_accounts}")
            logger.info(
                f"📊 Будет использовано {initial_accounts_to_request} аккаунтов, работа может выполниться не полностью")

        # Получаем начальные аккаунты
        module_name = f"inviter_{self.profile_name}"
        allocated_accounts = self.account_manager.get_free_accounts(module_name, initial_accounts_to_request)

        if not allocated_accounts:
            logger.error("❌ Не удалось получить свободные аккаунты")
            return

        logger.info(f"✅ Получено аккаунтов на старте: {len(allocated_accounts)}")

        # Создаем потоки для чатов
        chat_index = 0
        account_index = 0

        while self.chat_queue.qsize() > 0 and not self.stop_flag.is_set():
            try:
                chat = self.chat_queue.get_nowait()

                # Проверяем есть ли аккаунты для этого чата
                if account_index >= len(allocated_accounts):
                    # Пробуем получить еще аккаунты
                    additional_accounts = self.account_manager.get_free_accounts(
                        module_name,
                        self.config.threads_per_chat
                    )

                    if additional_accounts:
                        allocated_accounts.extend(additional_accounts)
                        logger.info(f"✅ Получено дополнительно {len(additional_accounts)} аккаунтов")
                    else:
                        # Возвращаем чат обратно в очередь
                        self.chat_queue.put(chat)
                        logger.warning(f"⚠️ Нет аккаунтов для чата {chat}, отложен")
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
                    logger.warning(f"⚠️ Не удалось выделить аккаунты для чата {chat}")
                    break

                # Создаем поток для чата
                thread = ChatWorkerThread(
                    chat_id=chat_index + 1,
                    chat_link=chat,
                    accounts=chat_accounts,
                    parent=self
                )
                thread.start()
                self.chat_threads.append(thread)
                chat_index += 1

                logger.info(f"✅ Запущен поток для чата #{chat_index}: {chat} (аккаунтов: {len(chat_accounts)})")

            except queue.Empty:
                break

        # Ждем завершения всех потоков
        self._wait_for_threads()

        # Обрабатываем отложенные чаты если остались
        if self.chat_queue.qsize() > 0:
            logger.warning(f"⚠️ Остались необработанные чаты: {self.chat_queue.qsize()}")

        # Выводим итоговую статистику
        self._print_final_stats()

    def _wait_for_threads(self):
        """Ждет завершения всех потоков"""
        logger.info("⏳ Ожидание завершения потоков...")

        while not self.stop_flag.is_set():
            alive = [t for t in self.chat_threads if t.is_alive()]

            if not alive:
                logger.info("✅ Все потоки завершены")
                break

            # Проверяем условие остановки
            if self.user_queue.empty() and self.total_processed > 0:
                logger.info("✅ Все пользователи обработаны")
                # НЕ останавливаем сразу, даем потокам завершиться корректно
                # self.stop()
                # break

            # Выводим промежуточную статистику
            free_accounts = self.account_manager.get_free_accounts_count()
            logger.info(
                f"📊 Активных потоков: {len(alive)} | Обработано: {self.total_processed} | Успешно: {self.total_success} | Свободных аккаунтов: {free_accounts}")

            self.stop_flag.wait(10)

        # Ждем завершения потоков
        for thread in self.chat_threads:
            if thread.is_alive():
                thread.join(timeout=30)  # Увеличиваем таймаут

    def update_account_stats(self, account_name: str, success: bool = False,
                             spam_block: bool = False, error: bool = False):
        """Обновляет статистику аккаунта"""
        if account_name not in self.account_stats:
            self.account_stats[account_name] = AccountStats(name=account_name)

        stats = self.account_stats[account_name]

        if success:
            stats.invites += 1
            self.total_success += 1
        if error:
            stats.errors += 1
            self.total_errors += 1
        if spam_block:
            stats.spam_blocks += 1
            stats.consecutive_spam += 1
        else:
            stats.consecutive_spam = 0

        self.total_processed += 1

    def _print_final_stats(self):
        """Выводит финальную статистику"""
        logger.info("=" * 60)
        logger.info("📊 ИТОГОВАЯ СТАТИСТИКА:")
        logger.info(f"   Всего обработано: {self.total_processed}")
        logger.info(f"   Успешных инвайтов: {self.total_success}")
        logger.info(f"   Ошибок: {self.total_errors}")

        if self.total_processed > 0:
            success_rate = (self.total_success / self.total_processed) * 100
            logger.info(f"   Процент успеха: {success_rate:.1f}%")

        logger.info("\n📊 СТАТИСТИКА ПО АККАУНТАМ:")
        for account_name, stats in self.account_stats.items():
            logger.info(
                f"   {account_name}: инвайтов={stats.invites}, ошибок={stats.errors}, спамблоков={stats.spam_blocks}")

        logger.info("=" * 60)


class ChatWorkerThread(threading.Thread):
    """Рабочий поток для одного чата"""

    def __init__(self, chat_id: int, chat_link: str, accounts: List, parent: ClassicInviterProcess):
        super().__init__(name=f"Chat-{chat_id}")
        self.chat_id = chat_id
        self.chat_link = chat_link
        self.accounts = accounts  # Аккаунты выделенные для этого чата
        self.parent = parent

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

            # Запускаем работу
            loop.run_until_complete(self._work())

        except Exception as e:
            logger.error(f"❌ [Chat-{self.chat_id}] Ошибка: {e}")
        finally:
            loop.close()

    async def _work(self):
        """Основная работа с чатом - ИСПРАВЛЕННАЯ ВЕРСИЯ С ПОТОКАМИ"""
        logger.info(f"🚀 [Chat-{self.chat_id}] Начинаем работу с {self.chat_link}")
        logger.info(f"👥 [Chat-{self.chat_id}] Доступно аккаунтов: {len(self.accounts)}")

        # Флаг завершения работы чата
        chat_completed = False

        # Счетчик активных воркеров для этого чата
        active_workers = []
        active_workers_lock = threading.Lock()

        # Пока не завершена работа с чатом
        while not chat_completed and not self.parent.stop_flag.is_set():
            # Запускаем воркеров в отдельных потоках
            worker_threads = []

            for i, account_data in enumerate(self.accounts):
                # Создаем поток для каждого аккаунта
                worker_thread = threading.Thread(
                    target=self._run_worker_in_thread,
                    args=(i + 1, account_data, active_workers, active_workers_lock),
                    name=f"Chat-{self.chat_id}-Worker-{i + 1}"
                )
                worker_thread.start()
                worker_threads.append(worker_thread)

            logger.info(f"🚀 [Chat-{self.chat_id}] Запущено {len(worker_threads)} потоков воркеров")

            # НЕ ЖДЕМ завершения всех! Просто проверяем статус периодически
            while not self.parent.stop_flag.is_set():
                # Ждем немного
                await asyncio.sleep(2)

                # Проверяем сколько воркеров еще работает
                with active_workers_lock:
                    still_working = len(active_workers)

                if still_working == 0:
                    logger.info(f"✅ [Chat-{self.chat_id}] Все воркеры завершили работу")
                    break

                # Проверяем условия завершения
                if self.parent.config.success_per_chat > 0 and self.chat_success >= self.parent.config.success_per_chat:
                    logger.success(f"✅ [Chat-{self.chat_id}] Достигнут лимит успешных инвайтов: {self.chat_success}")
                    chat_completed = True
                    break

                if self.parent.user_queue.empty():
                    logger.info(f"✅ [Chat-{self.chat_id}] Закончились пользователи для инвайта")
                    # Даем воркерам доработать текущих пользователей
                    await asyncio.sleep(5)
                    chat_completed = True
                    break

                logger.debug(
                    f"📊 [Chat-{self.chat_id}] Активных воркеров: {still_working}, успешных инвайтов: {self.chat_success}")

            # Теперь освобождаем аккаунты которые уже закончили работу
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

            logger.info(f"🔓 [Chat-{self.chat_id}] Освобождено завершивших работу аккаунтов: {released_count}")

            # Проверяем нужно ли продолжать работу
            if chat_completed:
                break

            # Если есть пользователи и работа не завершена - запрашиваем новые аккаунты
            if not self.parent.user_queue.empty():
                logger.info(f"🔄 [Chat-{self.chat_id}] Запрашиваем новые аккаунты для продолжения работы")

                new_accounts = self.parent.account_manager.get_multiple_free_accounts(
                    module_name,
                    self.parent.config.threads_per_chat
                )

                if not new_accounts:
                    logger.warning(f"⚠️ [Chat-{self.chat_id}] Нет свободных аккаунтов, завершаем работу с чатом")
                    chat_completed = True
                    break

                self.accounts = new_accounts
                logger.info(f"✅ [Chat-{self.chat_id}] Получено новых аккаунтов: {len(new_accounts)}")

        # Финальная очистка - ждем оставшиеся потоки
        logger.info(f"🧹 [Chat-{self.chat_id}] Ожидаем завершения оставшихся воркеров...")

        # Даем воркерам время завершиться
        await asyncio.sleep(5)

        # Освобождаем все оставшиеся аккаунты
        module_name = f"inviter_{self.parent.profile_name}"
        for account_data in self.accounts:
            self.parent.account_manager.release_account(account_data.name, module_name)

        logger.info(f"✅ [Chat-{self.chat_id}] Работа завершена")
        logger.info(
            f"📊 [Chat-{self.chat_id}] Итоговая статистика: обработано={self.chat_processed}, успешно={self.chat_success}, ошибок={self.chat_errors}")

    def _run_worker_in_thread(self, worker_id: int, account_data, active_workers: list, lock: threading.Lock):
        """Обертка для запуска воркера в отдельном потоке"""
        # Добавляем себя в список активных
        with lock:
            active_workers.append(account_data.name)

        try:
            # Создаем новый event loop для этого потока
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # Запускаем асинхронного воркера
            loop.run_until_complete(self._run_worker(worker_id, account_data))

            loop.close()
        except Exception as e:
            logger.error(f"❌ [Worker-{worker_id}] Ошибка в потоке: {e}")
        finally:
            # Удаляем себя из списка активных
            with lock:
                if account_data.name in active_workers:
                    active_workers.remove(account_data.name)

            # Освобождаем аккаунт сразу после завершения работы
            module_name = f"inviter_{self.parent.profile_name}"
            self.parent.account_manager.release_account(account_data.name, module_name)
            logger.info(f"🔓 [Worker-{worker_id}] Аккаунт {account_data.name} освобожден")

    async def _run_worker(self, worker_id: int, account_data):
        """Воркер для инвайтинга"""
        account_name = account_data.name
        account = account_data.account

        logger.info(f"👷 [Chat-{self.chat_id}][Worker-{worker_id}] Запуск с аккаунтом {account_name}")

        try:
            # Инициализация Telethon клиента
            await account.create_client()

            if not await account.connect():
                logger.error(f"❌ [Worker-{worker_id}] Не удалось подключить {account_name}")
                return

            # Проверяем авторизацию
            if not await account.client.is_user_authorized():
                logger.error(f"❌ [Worker-{worker_id}] Аккаунт {account_name} не авторизован")
                await account.disconnect()
                return

            # Получаем информацию о себе для проверки
            try:
                me = await account.client.get_me()
                logger.info(
                    f"✅ [Worker-{worker_id}] Подключен как {me.first_name} {me.last_name or ''} (@{me.username or 'no_username'})")
            except Exception as e:
                logger.error(f"❌ [Worker-{worker_id}] Ошибка получения информации об аккаунте: {e}")
                await account.disconnect()
                return

            # Присоединяемся к чату
            join_result = await self._join_chat(account, worker_id)
            if not join_result:
                logger.error(f"❌ [Worker-{worker_id}] Не удалось присоединиться к чату")
                await account.disconnect()
                return

            invites_count = 0
            errors_count = 0

            # Основной цикл инвайтинга
            while not self.parent.stop_flag.is_set():
                # Проверяем лимит успешных для чата
                if self.parent.config.success_per_chat > 0:
                    if self.chat_success >= self.parent.config.success_per_chat:
                        logger.info(
                            f"🎯 [Chat-{self.chat_id}] Достигнут лимит успешных инвайтов для чата: {self.chat_success}")
                        break

                # Проверяем лимит для аккаунта
                if self.parent.config.success_per_account > 0:
                    if invites_count >= self.parent.config.success_per_account:
                        logger.info(f"🎯 [Worker-{worker_id}] Достигнут лимит инвайтов для аккаунта: {invites_count}")
                        break

                # Получаем пользователя
                try:
                    user = self.parent.user_queue.get_nowait()
                except queue.Empty:
                    logger.info(f"✅ [Worker-{worker_id}] Очередь пуста")
                    break

                # Инвайтим пользователя
                success = await self._invite_user(user, account, account_name, worker_id)

                if success:
                    invites_count += 1
                    self.chat_success += 1
                else:
                    errors_count += 1

                self.chat_processed += 1

                # Обновляем статистику аккаунта
                self.parent.update_account_stats(
                    account_name,
                    success=success,
                    spam_block=(user.status == UserStatus.SPAM_BLOCK),
                    error=(not success)
                )

                # Задержка между инвайтами
                if self.parent.config.delay_between > 0:
                    await asyncio.sleep(self.parent.config.delay_between)

            logger.info(f"📊 [Worker-{worker_id}] Завершен. Инвайтов: {invites_count}, ошибок: {errors_count}")

        except Exception as e:
            logger.error(f"❌ [Worker-{worker_id}] Критическая ошибка: {e}")
        finally:
            # Отключаемся от Telegram
            try:
                await account.disconnect()
            except:
                pass

    async def _join_chat(self, account, worker_id: int) -> bool:
        """Присоединяется к чату"""
        try:
            await account.client(JoinChannelRequest(self.chat_link))
            logger.info(f"✅ [Worker-{worker_id}] Присоединился к чату {self.chat_link}")

            # Задержка после присоединения
            if self.parent.config.delay_after_start > 0:
                await asyncio.sleep(self.parent.config.delay_after_start)

            return True

        except Exception as e:
            error_text = str(e)
            if "already a participant" in error_text.lower():
                logger.info(f"ℹ️ [Worker-{worker_id}] Уже в чате {self.chat_link}")
                return True
            elif "wait" in error_text.lower():
                logger.warning(f"⏳ [Worker-{worker_id}] Нужно подождать перед присоединением")
                return False
            else:
                logger.error(f"❌ [Worker-{worker_id}] Ошибка присоединения к чату: {e}")
                return False

    async def _invite_user(self, user: InviteUser, account, account_name: str, worker_id: int) -> bool:
        """Инвайт пользователя через Telethon"""
        client = account.client

        if not client or not client.is_connected():
            logger.error(f"❌ [Worker-{worker_id}][{account_name}] Клиент не подключен")
            return False

        username = user.username
        if username.startswith('@'):
            username = username[1:]

        logger.info(f"📨 [Worker-{worker_id}][{account_name}] Пытаемся добавить @{username} в {self.chat_link}")

        try:
            # 1. Проверяем существование пользователя и получаем количество общих чатов
            try:
                full_user = await client(GetFullUserRequest(username))
                old_common_chats = full_user.full_user.common_chats_count
            except (ValueError, TypeError, UsernameInvalidError, UsernameNotOccupiedError):
                logger.warning(f"❓ [Worker-{worker_id}] Пользователь @{username} не существует")
                user.status = UserStatus.NOT_FOUND
                user.last_attempt = datetime.now()
                user.error_message = "Пользователь не найден"
                self.parent.processed_users[username] = user
                return False

            # 2. Пытаемся пригласить
            result = await client(InviteToChannelRequest(
                channel=self.chat_link,
                users=[username]
            ))

            # Проверяем есть ли missing_invitees (приватность)
            if result.missing_invitees:
                logger.warning(f"🔒 [Worker-{worker_id}] @{username} - настройки приватности")
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
                logger.warning(f"💸 [Worker-{worker_id}] @{username} добавлен и сразу списан")
                user.status = UserStatus.ERROR
                user.last_attempt = datetime.now()
                user.error_message = "Списание"
                self.parent.processed_users[username] = user
                return False

            # Успешно добавлен
            logger.success(f"✅ [Worker-{worker_id}][{account_name}] @{username} успешно добавлен!")
            user.status = UserStatus.INVITED
            user.last_attempt = datetime.now()
            self.parent.processed_users[username] = user
            return True

        except (PeerFloodError, FloodWaitError) as e:
            logger.error(f"🚫 [Worker-{worker_id}][{account_name}] Спамблок при добавлении @{username}")
            user.status = UserStatus.SPAM_BLOCK
            user.last_attempt = datetime.now()
            user.error_message = "Спамблок"
            self.parent.processed_users[username] = user
            return False

        except UserPrivacyRestrictedError:
            logger.warning(f"🔒 [Worker-{worker_id}] @{username} - настройки приватности")
            user.status = UserStatus.PRIVACY
            user.last_attempt = datetime.now()
            user.error_message = "Настройки приватности"
            self.parent.processed_users[username] = user
            return False

        except (UserDeactivatedBanError, UserDeactivatedError):
            logger.warning(f"🚫 [Worker-{worker_id}] @{username} заблокирован в Telegram")
            user.status = UserStatus.NOT_FOUND
            user.last_attempt = datetime.now()
            user.error_message = "Пользователь заблокирован"
            self.parent.processed_users[username] = user
            return False

        except (ChatAdminRequiredError, ChatWriteForbiddenError):
            logger.error(f"❌ [Worker-{worker_id}] Недостаточно прав в чате {self.chat_link}")
            user.status = UserStatus.ERROR
            user.last_attempt = datetime.now()
            user.error_message = "Недостаточно прав в чате"
            self.parent.processed_users[username] = user
            return False

        except ChannelsTooMuchError:
            logger.warning(f"📊 [Worker-{worker_id}] @{username} уже в максимальном количестве чатов")
            user.status = UserStatus.ERROR
            user.last_attempt = datetime.now()
            user.error_message = "Максимум чатов"
            self.parent.processed_users[username] = user
            return False

        except Exception as e:
            # Специфичные ошибки по тексту
            error_text = str(e)

            if "CHAT_MEMBER_ADD_FAILED" in error_text:
                logger.error(f"❌ [Worker-{worker_id}] Не удалось добавить @{username}")
                user.status = UserStatus.ERROR
                user.error_message = "Ошибка добавления"

            elif "You're banned from sending messages" in error_text:
                logger.error(f"🚫 [Worker-{worker_id}][{account_name}] Аккаунт заблокирован для инвайтов")
                user.status = UserStatus.ERROR
                user.error_message = "Аккаунт заблокирован"

            elif "user was kicked" in error_text.lower():
                logger.warning(f"🚫 [Worker-{worker_id}] @{username} был ранее кикнут из чата")
                user.status = UserStatus.ALREADY_IN
                user.error_message = "Был кикнут"

            elif "already in too many channels" in error_text.lower():
                logger.warning(f"📊 [Worker-{worker_id}] @{username} в слишком многих чатах")
                user.status = UserStatus.ERROR
                user.error_message = "Слишком много чатов"

            else:
                logger.error(f"❌ [Worker-{worker_id}] Неизвестная ошибка для @{username}: {e}")
                user.status = UserStatus.ERROR
                user.error_message = f"Ошибка: {error_text[:50]}"

            user.last_attempt = datetime.now()
            self.parent.processed_users[username] = user
            return False