# src/modules/impl/inviter/classic_inviter_simple.py
"""
Классический режим инвайтинга - упрощенная версия
"""

import threading
import asyncio
import queue
from typing import Dict, Optional
from datetime import datetime
from loguru import logger

from .base_inviter_simple import BaseInviterProcess
from src.entities.modules.inviter import InviteUser, UserStatus


class ClassicInviterProcess(BaseInviterProcess):
    """Классический инвайтер - один поток на чат"""

    def __init__(self, profile_name: str, profile_data: Dict, accounts_list: list):
        super().__init__(profile_name, profile_data, accounts_list)
        self.chat_threads = []

    def _run_inviting(self):
        """Запускает классический инвайтинг"""
        logger.info("🚀 Запуск классического инвайтинга")

        # Задержка после старта
        if self.config.delay_after_start > 0:
            logger.info(f"⏳ Задержка {self.config.delay_after_start} сек...")
            self.stop_flag.wait(self.config.delay_after_start)

        # Создаем потоки для каждого чата
        chat_count = self.chat_queue.qsize()
        logger.info(f"💬 Создаем потоки для {chat_count} чатов")

        for i in range(chat_count):
            if self.stop_flag.is_set():
                break

            try:
                chat = self.chat_queue.get_nowait()

                # Создаем поток для чата
                thread = ChatWorkerThread(
                    chat_id=i + 1,
                    chat_link=chat,
                    parent=self
                )
                thread.start()
                self.chat_threads.append(thread)

                logger.info(f"✅ Запущен поток для чата #{i + 1}: {chat}")

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

            # Проверяем условия остановки
            if self.account_pool.get_active_count() == 0:
                logger.error("❌ Нет активных аккаунтов")
                self.stop()
                break

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

    def __init__(self, chat_id: int, chat_link: str, parent: ClassicInviterProcess):
        super().__init__(name=f"Chat-{chat_id}")
        self.chat_id = chat_id
        self.chat_link = chat_link
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

        # Создаем worker-ы согласно настройке
        workers_count = self.parent.config.threads_per_chat
        logger.info(f"🔧 [Chat-{self.chat_id}] Создаем {workers_count} воркеров")

        # Запускаем воркеров
        tasks = []
        for i in range(workers_count):
            task = asyncio.create_task(
                self._run_worker(i + 1)
            )
            tasks.append(task)

        # Ждем завершения
        await asyncio.gather(*tasks, return_exceptions=True)

        logger.info(f"✅ [Chat-{self.chat_id}] Работа завершена")

    async def _run_worker(self, worker_id: int):
        """Воркер для инвайтинга"""
        logger.info(f"👷 [Chat-{self.chat_id}][Worker-{worker_id}] Запуск")

        # Получаем аккаунт
        account = self.parent.account_pool.get_account()
        if not account:
            logger.error(f"❌ [Worker-{worker_id}] Нет доступных аккаунтов")
            return

        account_name = account.get('name', 'unknown')

        try:
            # TODO: Здесь будет инициализация Telethon

            # Основной цикл
            while not self.parent.stop_flag.is_set():
                # Проверяем паузу
                if self.parent.pause_flag.is_set():
                    await asyncio.sleep(1)
                    continue

                # Получаем пользователя
                try:
                    user = self.parent.user_queue.get_nowait()
                except queue.Empty:
                    logger.info(f"✅ [Worker-{worker_id}] Очередь пуста")
                    break

                # Инвайтим пользователя
                success = await self._invite_user(user, account_name, worker_id)

                # Обновляем статистику
                self.parent.account_pool.update_stats(
                    account_name,
                    success=success,
                    error_type='spam_block' if not success else None
                )

                # Проверяем нужно ли заблокировать аккаунт
                if self.parent.account_pool.should_block_account(
                        account_name,
                        self.parent.config.__dict__
                ):
                    logger.warning(f"🚫 [Worker-{worker_id}] Аккаунт заблокирован")
                    break

                # Задержка между инвайтами
                if self.parent.config.delay_between > 0:
                    await asyncio.sleep(self.parent.config.delay_between)

        finally:
            # Возвращаем аккаунт
            should_block = self.parent.account_pool.should_block_account(
                account_name,
                self.parent.config.__dict__
            )
            self.parent.account_pool.release_account(account, block=should_block)

            logger.info(f"⏹️ [Worker-{worker_id}] Завершен")

    async def _invite_user(self, user: InviteUser, account_name: str,
                           worker_id: int) -> bool:
        """Инвайт пользователя (заглушка)"""
        logger.info(f"📨 [Worker-{worker_id}][{account_name}] Инвайт @{user.username}")

        # TODO: Здесь будет реальный инвайт через Telethon
        # Пока симулируем
        await asyncio.sleep(1)

        # Обновляем статус
        user.status = UserStatus.INVITED
        user.last_attempt = datetime.now()
        self.parent.processed_users[user.username] = user

        return True