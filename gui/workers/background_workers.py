# gui/workers/background_workers.py - НОВАЯ СИСТЕМА ФОНОВЫХ РАБОЧИХ
"""
Система фоновых рабочих потоков для предотвращения блокировки GUI
"""

from PySide6.QtCore import QThread, Signal, QTimer, QMutex, QMutexLocker
from typing import Dict, List, Optional, Callable
from loguru import logger
import time
import threading
from collections import defaultdict


class ProfileStatsWorker(QThread):
    """Фоновый рабочий для получения статистики профилей"""

    # Сигналы
    stats_updated = Signal(str, dict)  # profile_name, stats_data
    error_occurred = Signal(str, str)  # profile_name, error_message

    def __init__(self):
        super().__init__()
        self.mutex = QMutex()
        self.profiles_to_update = set()
        self.update_interval = 2.0  # Секунды между обновлениями
        self.running = True
        self.stats_cache = {}
        self.last_update_times = {}

        # Флаг для контроля нагрузки
        self.max_concurrent_updates = 3
        self.current_updates = 0

    def add_profile(self, profile_name: str):
        """Добавляет профиль для мониторинга"""
        with QMutexLocker(self.mutex):
            self.profiles_to_update.add(profile_name)

    def remove_profile(self, profile_name: str):
        """Убирает профиль из мониторинга"""
        with QMutexLocker(self.mutex):
            self.profiles_to_update.discard(profile_name)
            self.stats_cache.pop(profile_name, None)
            self.last_update_times.pop(profile_name, None)

    def stop_worker(self):
        """Останавливает рабочий поток"""
        self.running = False
        self.quit()
        self.wait()

    def run(self):
        """Основной цикл рабочего потока"""
        logger.info("📊 ProfileStatsWorker запущен")

        while self.running:
            try:
                # Получаем копию списка профилей
                with QMutexLocker(self.mutex):
                    profiles_copy = list(self.profiles_to_update)

                # Обновляем статистику для каждого профиля
                for profile_name in profiles_copy:
                    if not self.running:
                        break

                    # Проверяем нужно ли обновлять этот профиль
                    if self._should_update_profile(profile_name):
                        # Ограничиваем количество одновременных обновлений
                        if self.current_updates < self.max_concurrent_updates:
                            self._update_profile_stats(profile_name)

                    # Небольшая пауза между профилями
                    self.msleep(100)

                # Пауза между циклами
                self.msleep(int(self.update_interval * 1000))

            except Exception as e:
                logger.error(f"❌ Ошибка в ProfileStatsWorker: {e}")
                self.msleep(1000)

        logger.info("📊 ProfileStatsWorker остановлен")

    def _should_update_profile(self, profile_name: str) -> bool:
        """Проверяет нужно ли обновлять профиль"""
        current_time = time.time()
        last_update = self.last_update_times.get(profile_name, 0)

        return (current_time - last_update) >= self.update_interval

    def _update_profile_stats(self, profile_name: str):
        """Обновляет статистику конкретного профиля"""
        try:
            self.current_updates += 1
            start_time = time.time()

            # Получаем статистику из модуля
            stats_data = self._get_profile_stats_from_module(profile_name)

            # Проверяем изменились ли данные
            old_stats = self.stats_cache.get(profile_name, {})
            if stats_data != old_stats:
                # Данные изменились - отправляем сигнал
                self.stats_cache[profile_name] = stats_data
                self.stats_updated.emit(profile_name, stats_data)

            self.last_update_times[profile_name] = time.time()

            # Логируем производительность
            duration = time.time() - start_time
            if duration > 0.5:  # Предупреждение если обновление слишком долгое
                logger.warning(f"⚠️ Медленное обновление {profile_name}: {duration:.2f}s")

        except Exception as e:
            logger.error(f"❌ Ошибка обновления статистики {profile_name}: {e}")
            self.error_occurred.emit(profile_name, str(e))
        finally:
            self.current_updates -= 1

    def _get_profile_stats_from_module(self, profile_name: str) -> dict:
        """Получает статистику профиля из модуля - БЫСТРО"""
        try:
            from src.modules.impl.inviter import get_profile_progress

            # Получаем только базовую статистику для UI
            progress_data = get_profile_progress(profile_name)

            if progress_data:
                return {
                    'success': progress_data.get('success', 0),
                    'errors': progress_data.get('errors', 0),
                    'total_goal': progress_data.get('total_goal', 0),
                    'speed': progress_data.get('speed', 0),
                    'status': progress_data.get('status', 'Неизвестно'),
                    'is_running': self._check_if_running(profile_name)
                }
            else:
                return {
                    'success': 0,
                    'errors': 0,
                    'total_goal': 0,
                    'speed': 0,
                    'status': 'Остановлен',
                    'is_running': False
                }

        except Exception as e:
            logger.error(f"❌ Ошибка получения статистики из модуля: {e}")
            return {}

    def _check_if_running(self, profile_name: str) -> bool:
        """Быстрая проверка работает ли профиль"""
        try:
            from src.modules.impl.inviter.inviter_manager import _inviter_module_manager

            if _inviter_module_manager:
                return profile_name in _inviter_module_manager.active_processes
            return False
        except:
            return False


class ChatStatsWorker(QThread):
    """Фоновый рабочий для статистики чатов (более тяжелые операции)"""

    chat_stats_updated = Signal(str, dict)  # profile_name, chat_stats

    def __init__(self):
        super().__init__()
        self.mutex = QMutex()
        self.profiles_to_update = set()
        self.update_interval = 5.0  # Реже чем основные статистики
        self.running = True

    def add_profile(self, profile_name: str):
        """Добавляет профиль для мониторинга чатов"""
        with QMutexLocker(self.mutex):
            self.profiles_to_update.add(profile_name)

    def remove_profile(self, profile_name: str):
        """Убирает профиль из мониторинга чатов"""
        with QMutexLocker(self.mutex):
            self.profiles_to_update.discard(profile_name)

    def stop_worker(self):
        """Останавливает рабочий поток"""
        self.running = False
        self.quit()
        self.wait()

    def run(self):
        """Основной цикл для обновления статистики чатов"""
        logger.info("💬 ChatStatsWorker запущен")

        while self.running:
            try:
                with QMutexLocker(self.mutex):
                    profiles_copy = list(self.profiles_to_update)

                for profile_name in profiles_copy:
                    if not self.running:
                        break

                    # Получаем детальную статистику чатов
                    chat_stats = self._get_chat_stats_from_module(profile_name)
                    if chat_stats:
                        self.chat_stats_updated.emit(profile_name, chat_stats)

                    # Пауза между профилями
                    self.msleep(500)

                # Длинная пауза между циклами
                self.msleep(int(self.update_interval * 1000))

            except Exception as e:
                logger.error(f"❌ Ошибка в ChatStatsWorker: {e}")
                self.msleep(2000)

        logger.info("💬 ChatStatsWorker остановлен")

    def _get_chat_stats_from_module(self, profile_name: str) -> dict:
        """Получает детальную статистику чатов"""
        try:
            # Тяжелая операция - выполняется в фоне
            from src.modules.impl.inviter.inviter_manager import _inviter_module_manager

            if not _inviter_module_manager:
                return {}

            if profile_name not in _inviter_module_manager.active_processes:
                return {}

            process = _inviter_module_manager.active_processes[profile_name]

            # Собираем статистику чатов
            chat_stats = {}

            if hasattr(process, 'processed_users') and process.processed_users:
                # Тяжелая операция обработки статистики
                chat_stats = self._process_chat_statistics(process)

            return chat_stats

        except Exception as e:
            logger.error(f"❌ Ошибка получения статистики чатов: {e}")
            return {}

    def _process_chat_statistics(self, process) -> dict:
        """Обрабатывает статистику чатов - тяжелая операция"""
        # Эта операция теперь выполняется в фоне и не блокирует GUI
        try:
            from src.entities.moduls.inviter import UserStatus

            chat_stats = {}

            # Получаем список чатов
            chat_list = []
            if hasattr(process, 'chats_list') and process.chats_list:
                chat_list = process.chats_list[:5]
            else:
                chat_list = ["@test_chat"]

            # Инициализируем статистику
            for chat_link in chat_list:
                chat_stats[chat_link] = {
                    'success': 0,
                    'errors': 0,
                    'total': 0,
                    'goal': getattr(process.config, 'success_per_chat', 100) if hasattr(process, 'config') else 100
                }

            # Обрабатываем пользователей
            for username, user_data in process.processed_users.items():
                # Определяем чат (упрощенная логика)
                user_chat = chat_list[0]  # Для простоты берем первый чат

                if user_chat in chat_stats:
                    chat_stats[user_chat]['total'] += 1

                    if hasattr(user_data, 'status'):
                        if user_data.status == UserStatus.INVITED:
                            chat_stats[user_chat]['success'] += 1
                        else:
                            chat_stats[user_chat]['errors'] += 1

            return chat_stats

        except Exception as e:
            logger.error(f"❌ Ошибка обработки статистики: {e}")
            return {}


class WorkerManager:
    """Менеджер фоновых рабочих потоков"""

    def __init__(self):
        self.profile_stats_worker = None
        self.chat_stats_worker = None
        self.is_initialized = False

    def initialize(self):
        """Инициализирует всех рабочих"""
        if self.is_initialized:
            return

        try:
            # Создаем рабочих
            self.profile_stats_worker = ProfileStatsWorker()
            self.chat_stats_worker = ChatStatsWorker()

            # Запускаем
            self.profile_stats_worker.start()
            self.chat_stats_worker.start()

            self.is_initialized = True
            logger.info("✅ WorkerManager инициализирован")

        except Exception as e:
            logger.error(f"❌ Ошибка инициализации WorkerManager: {e}")

    def shutdown(self):
        """Корректно останавливает всех рабочих"""
        if not self.is_initialized:
            return

        try:
            if self.profile_stats_worker:
                self.profile_stats_worker.stop_worker()

            if self.chat_stats_worker:
                self.chat_stats_worker.stop_worker()

            self.is_initialized = False
            logger.info("✅ WorkerManager остановлен")

        except Exception as e:
            logger.error(f"❌ Ошибка остановки WorkerManager: {e}")

    def add_profile_monitoring(self, profile_name: str):
        """Добавляет профиль для мониторинга"""
        if self.profile_stats_worker:
            self.profile_stats_worker.add_profile(profile_name)
        if self.chat_stats_worker:
            self.chat_stats_worker.add_profile(profile_name)

    def remove_profile_monitoring(self, profile_name: str):
        """Убирает профиль из мониторинга"""
        if self.profile_stats_worker:
            self.profile_stats_worker.remove_profile(profile_name)
        if self.chat_stats_worker:
            self.chat_stats_worker.remove_profile(profile_name)


# Глобальный менеджер
_worker_manager = None


def get_worker_manager() -> WorkerManager:
    """Получает глобальный менеджер рабочих"""
    global _worker_manager
    if _worker_manager is None:
        _worker_manager = WorkerManager()
    return _worker_manager


def init_worker_manager():
    """Инициализирует систему фоновых рабочих"""
    manager = get_worker_manager()
    manager.initialize()
    return manager


def shutdown_worker_manager():
    """Останавливает систему фоновых рабочих"""
    global _worker_manager
    if _worker_manager:
        _worker_manager.shutdown()
        _worker_manager = None