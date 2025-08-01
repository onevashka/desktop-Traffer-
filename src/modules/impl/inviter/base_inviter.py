# src/modules/impl/inviter/base_inviter.py
"""
Простой базовый класс для инвайтера
"""

import threading
import queue
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List
from datetime import datetime
from loguru import logger

from src.entities.modules.inviter import InviterConfig
from .data_loader import InviterDataLoader


class BaseInviterProcess(threading.Thread, ABC):
    """Базовый класс для процессов инвайтинга"""

    def __init__(self, profile_name: str, profile_data: Dict, account_manager):
        super().__init__(name=f"Inviter-{profile_name}")

        # Основные данные
        self.profile_name = profile_name
        self.profile_data = profile_data
        self.profile_folder = Path(profile_data['folder_path'])

        # AccountManager для получения аккаунтов
        self.account_manager = account_manager

        # Загрузчик данных
        self.data_loader = InviterDataLoader(self.profile_folder)

        # Конфигурация
        config_dict = profile_data.get('config', {})
        self.config = self.data_loader.load_config(config_dict)

        # Флаги управления
        self.stop_flag = threading.Event()
        self.is_running = False

        # Очереди данных
        self.chat_queue = queue.Queue()
        self.user_queue = queue.Queue()

        # Обработанные пользователи
        self.processed_users = {}

        # Время работы
        self.started_at = None
        self.finished_at = None

        logger.info(f"📨 Инициализирован {self.config.invite_type} процесс: {profile_name}")

    def run(self):
        """Основной метод потока"""
        try:
            logger.info(f"🚀 Запуск процесса: {self.profile_name}")
            self.is_running = True
            self.started_at = datetime.now()

            # 1. Загружаем данные (чаты и пользователей)
            if not self._load_data():
                logger.error("❌ Не удалось загрузить данные")
                return

            # 2. Проверяем есть ли активные аккаунты
            if not self._check_accounts():
                logger.error("❌ Нет активных аккаунтов")
                return

            # 3. Запускаем основную работу
            self._run_inviting()

        except Exception as e:
            logger.error(f"❌ Критическая ошибка: {e}")
        finally:
            self.finished_at = datetime.now()
            self._cleanup()
            self.is_running = False
            logger.info(f"⏹️ Процесс остановлен: {self.profile_name}")

    def _load_data(self) -> bool:
        """Загружает все необходимые данные"""
        try:
            # Загружаем чаты
            chats, chat_count = self.data_loader.load_chats()
            if not chats:
                logger.error("❌ Нет чатов для инвайта")
                return False

            for chat in chats:
                self.chat_queue.put(chat)

            # Загружаем пользователей
            self.user_queue, self.processed_users, clean_count, dirty_count = \
                self.data_loader.load_users()

            if clean_count == 0:
                logger.error("❌ Нет пользователей для инвайта")
                return False

            logger.info(f"✅ Загружено: {chat_count} чатов, {clean_count} пользователей")
            return True

        except Exception as e:
            logger.error(f"❌ Ошибка загрузки данных: {e}")
            return False

    def _check_accounts(self) -> bool:
        """Проверяет наличие активных аккаунтов"""
        # Получаем активные аккаунты из трафика
        active_accounts = [
            acc for acc in self.account_manager.traffic_accounts.values()
            if acc.status == "active"
        ]

        if not active_accounts:
            logger.error("❌ Нет активных аккаунтов в папке трафика")
            return False

        logger.info(f"✅ Найдено активных аккаунтов: {len(active_accounts)}")
        return True

    def get_available_accounts(self) -> List:
        """Получает список доступных аккаунтов"""
        # Возвращаем все активные аккаунты из трафика
        return [
            acc for acc in self.account_manager.traffic_accounts.values()
            if acc.status == "active"
        ]

    @abstractmethod
    def _run_inviting(self):
        """Основная логика инвайтинга (реализуется в наследниках)"""
        pass

    def _cleanup(self):
        """Очистка при завершении"""
        logger.info("🧹 Сохранение прогресса...")

        # Сохраняем прогресс пользователей
        self.data_loader.save_users_progress(
            self.processed_users,
            self.user_queue
        )

        # Выводим статистику
        if self.started_at and self.finished_at:
            duration = (self.finished_at - self.started_at).total_seconds() / 60
            logger.info(f"⏱️ Время работы: {duration:.1f} минут")

    def stop(self):
        """Останавливает процесс"""
        logger.info(f"⏸️ Остановка процесса: {self.profile_name}")
        self.stop_flag.set()