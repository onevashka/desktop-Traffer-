# src/modules/impl/inviter/classic_inviter.py
"""
Классический режим инвайтинга - простая версия
"""

import threading
import asyncio
import queue
import random
from typing import Dict, List
from datetime import datetime
from loguru import logger

from .base_inviter import BaseInviterProcess
from src.entities.modules.inviter import InviteUser, UserStatus


class ClassicInviterProcess(BaseInviterProcess):
    """Классический инвайтер - один поток на чат"""

    def __init__(self, profile_name: str, profile_data: Dict, account_manager):
        super().__init__(profile_name, profile_data, account_manager)
        self.chat_threads = []

    def _run_inviting(self):
        """Запускает классический инвайтинг"""
        logger.info("🚀 Запуск классического инвайтинга")

        # Получаем доступные аккаунты
        available_accounts = self.get_available_accounts()
        if not available_accounts:
            logger.error("❌ Нет доступных аккаунтов")
            return

        # Задержка после старта
        if self.config.delay_after_start > 0:
            logger.info(f"⏳ Задержка {self.config.delay_after_start} сек...")
            self.stop_flag.wait(self.config.delay_after_start)

        # Создаем потоки для каждого чата
        chat_count = self.chat_queue.qsize()
        logger.info(f"💬 Создаем потоки для {chat_count} чатов")

        # Распределяем аккаунты между чатами
        accounts_per_chat = max(1, len(available_accounts) // chat_count)

        account_index = 0
        for i in range(chat_count):
            if self.stop_flag.is_set():
                break

            try:
                chat = self.chat_queue.get_nowait()

                # Выделяем аккаунты для этого чата
                chat_accounts = []
                for j in range(self.config.threads_per_chat):
                    if account_index < len(available_accounts):
                        chat_accounts.append(available_accounts[account_index])
                        account_index += 1

                if not chat_accounts:
                    logger.warning(f"⚠️ Нет аккаунтов для чата #{i + 1}")
                    continue

                # Создаем поток для чата
                thread = ChatWorkerThread(
                    chat_id=i + 1,
                    chat_link=chat,
                    accounts=chat_accounts,
                    parent=self
                )
                thread.start()
                self.chat_threads.append(thread)

                logger.info(f"✅ Запущен поток для чата #{i + 1}: {chat} (аккаунтов: {len(chat_accounts)})")

            except queue.Empty:
                break

        # Ждем завершения всех потоков
        self._wait_for_threads()

    def _wait_for_threads(self):
        """Ждет завершения всех потоков"""
        logger.info("⏳ Ожидание завершения потоков...")

        while not self.stop_flag.is_set():
            alive = [t for t in self.chat_threads if t.is_alive()]

            if not alive:
                logger.info("✅ Все потоки завершены")
                break

            # Проверяем условие остановки
            if self.user_queue.empty() and len(self.processed_users) > 0:
                logger.info("✅ Все пользователи обработаны")
                self.stop()
                break

            self.stop_flag.wait(5)

        # Ждем завершения потоков
        for thread in self.chat_threads:
            if thread.is_alive():
                thread.join(timeout=10)


class ChatWorkerThread(threading.Thread):
    """Рабочий поток для одного чата"""

    def __init__(self, chat_id: int, chat_link: str, accounts: List, parent: ClassicInviterProcess):
        super().__init__(name=f"Chat-{chat_id}")
        self.chat_id = chat_id
        self.chat_link = chat_link
        self.accounts = accounts  # Аккаунты выделенные для этого чата
        self.parent = parent

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
        """Основная работа с чатом"""
        logger.info(f"🚀 [Chat-{self.chat_id}] Начинаем работу с {self.chat_link}")
        logger.info(f"👥 [Chat-{self.chat_id}] Доступно аккаунтов: {len(self.accounts)}")

        # Запускаем воркеров
        tasks = []
        for i, account_data in enumerate(self.accounts):
            task = asyncio.create_task(
                self._run_worker(i + 1, account_data)
            )
            tasks.append(task)

        # Ждем завершения
        await asyncio.gather(*tasks, return_exceptions=True)

        logger.info(f"✅ [Chat-{self.chat_id}] Работа завершена")

    async def _run_worker(self, worker_id: int, account_data):
        """Воркер для инвайтинга"""
        account_name = account_data.name
        logger.info(f"👷 [Chat-{self.chat_id}][Worker-{worker_id}] Запуск с аккаунтом {account_name}")

        try:
            # TODO: Здесь будет инициализация Telethon
            # account = account_data.account
            # await account.create_client()
            # await account.connect()

            invites_count = 0
            errors_count = 0

            # Основной цикл
            while not self.parent.stop_flag.is_set():
                # Получаем пользователя
                try:
                    user = self.parent.user_queue.get_nowait()
                except queue.Empty:
                    logger.info(f"✅ [Worker-{worker_id}] Очередь пуста")
                    break

                # Инвайтим пользователя
                success = await self._invite_user(user, account_name, worker_id)

                if success:
                    invites_count += 1
                else:
                    errors_count += 1

                # Проверяем лимиты
                if self.parent.config.success_per_account > 0:
                    if invites_count >= self.parent.config.success_per_account:
                        logger.info(f"🎯 [Worker-{worker_id}] Достигнут лимит инвайтов: {invites_count}")
                        break

                # Задержка между инвайтами
                if self.parent.config.delay_between > 0:
                    await asyncio.sleep(self.parent.config.delay_between)

            logger.info(f"📊 [Worker-{worker_id}] Завершен. Инвайтов: {invites_count}, ошибок: {errors_count}")

        except Exception as e:
            logger.error(f"❌ [Worker-{worker_id}] Критическая ошибка: {e}")

    async def _invite_user(self, user: InviteUser, account_name: str, worker_id: int) -> bool:
        """Инвайт пользователя (заглушка)"""
        logger.info(f"📨 [Worker-{worker_id}][{account_name}] Инвайт @{user.username}")

        # TODO: Здесь будет реальный инвайт через Telethon
        # Пока симулируем с рандомным результатом
        await asyncio.sleep(1)

        # Симулируем результат
        if random.random() > 0.1:  # 90% успех
            user.status = UserStatus.INVITED
            user.last_attempt = datetime.now()
            self.parent.processed_users[user.username] = user
            return True
        else:
            user.status = UserStatus.ERROR
            user.last_attempt = datetime.now()
            user.error_message = "Симуляция ошибки"
            self.parent.processed_users[user.username] = user
            return False