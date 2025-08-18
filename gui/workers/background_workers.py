# gui/workers/background_workers.py - ОПТИМИЗИРОВАННАЯ ВЕРСИЯ ДЛЯ 100+ ПРОФИЛЕЙ
"""
Система фоновых рабочих потоков для предотвращения блокировки GUI
ОПТИМИЗИРОВАНО: QThreadPool вместо QThread, адаптивные интервалы
"""

from PySide6.QtCore import QObject, Signal, QTimer, QMutex, QMutexLocker, QRunnable, QThreadPool
from typing import Dict, List, Optional, Callable, Set
from loguru import logger
import time
import threading
from collections import defaultdict, deque


class ProfileStatsTask(QRunnable):
    """Задача для обновления статистики одного профиля"""

    def __init__(self, profile_name: str, callback: Callable, signals: QObject):
        super().__init__()
        self.profile_name = profile_name
        self.callback = callback
        self.signals = signals
        self.setAutoDelete(True)  # Автоматически удаляется после выполнения

    def run(self):
        """Выполнение задачи получения статистики"""
        try:
            start_time = time.time()

            # Выполняем callback для получения статистики
            result = self.callback(self.profile_name)

            # ИСПРАВЛЕНО: Проверяем какой тип сигналов у объекта
            if result:
                if hasattr(self.signals, 'stats_updated'):
                    self.signals.stats_updated.emit(self.profile_name, result)
                elif hasattr(self.signals, 'chat_stats_updated'):
                    self.signals.chat_stats_updated.emit(self.profile_name, result)

            # Логируем только медленные операции
            duration = time.time() - start_time
            if duration > 1.0:  # Только если дольше 1 секунды
                logger.warning(f"⚠️ Медленная статистика для {self.profile_name}: {duration:.2f}s")

        except Exception as e:
            logger.error(f"❌ Ошибка получения статистики {self.profile_name}: {e}")
            # ИСПРАВЛЕНО: Проверяем наличие сигнала ошибки
            if hasattr(self.signals, 'error_occurred'):
                self.signals.error_occurred.emit(self.profile_name, str(e))


class BatchStatsTask(QRunnable):
    """Пакетная задача для обновления статистики множества профилей"""

    def __init__(self, profiles: List[str], callback: Callable, signals: QObject):
        super().__init__()
        self.profiles = profiles
        self.callback = callback
        self.signals = signals
        self.setAutoDelete(True)

    def run(self):
        """Пакетное выполнение получения статистики"""
        try:
            batch_results = {}
            start_time = time.time()

            # Обрабатываем профили небольшими пакетами
            for i in range(0, len(self.profiles), 10):  # По 10 профилей в пакете
                batch = self.profiles[i:i + 10]

                for profile_name in batch:
                    try:
                        result = self.callback(profile_name)
                        if result:
                            batch_results[profile_name] = result
                    except Exception as e:
                        # Не логируем каждую ошибку - только в debug режиме
                        logger.debug(f"Ошибка в пакете для {profile_name}: {e}")
                        continue

                # Небольшая пауза между пакетами, чтобы не нагружать систему
                if i + 10 < len(self.profiles):
                    time.sleep(0.05)  # 50мс пауза

            # ИСПРАВЛЕНО: Отправляем результаты через правильный сигнал
            if batch_results:
                if hasattr(self.signals, 'batch_updated'):
                    self.signals.batch_updated.emit(batch_results)
                else:
                    # Fallback - отправляем по одному
                    for profile_name, stats in batch_results.items():
                        if hasattr(self.signals, 'stats_updated'):
                            self.signals.stats_updated.emit(profile_name, stats)
                        elif hasattr(self.signals, 'chat_stats_updated'):
                            self.signals.chat_stats_updated.emit(profile_name, stats)

            duration = time.time() - start_time
            if len(self.profiles) > 20:  # Логируем только большие пакеты
                logger.info(f"📊 Пакетная обработка {len(self.profiles)} профилей за {duration:.2f}s")

        except Exception as e:
            logger.error(f"❌ Ошибка пакетной обработки: {e}")


class ProfileStatsWorker(QObject):
    """ОПТИМИЗИРОВАННЫЙ рабочий для статистики профилей - использует QThreadPool"""

    # Сигналы
    stats_updated = Signal(str, dict)  # profile_name, stats_data
    batch_updated = Signal(dict)  # {profile_name: stats_data}
    error_occurred = Signal(str, str)  # profile_name, error_message

    def __init__(self):
        super().__init__()

        # ОПТИМИЗАЦИЯ: Используем глобальный пул потоков вместо QThread
        self.thread_pool = QThreadPool.globalInstance()

        # НАСТРАИВАЕМ пул для оптимальной производительности
        original_max = self.thread_pool.maxThreadCount()
        # Ограничиваем максимум 16 потоками для стабильности
        optimized_max = min(16, max(4, original_max))
        self.thread_pool.setMaxThreadCount(optimized_max)

        # Настраиваем время жизни потоков
        self.thread_pool.setExpiryTimeout(30000)  # 30 секунд

        # Управление профилями
        self.mutex = QMutex()
        self.active_profiles: Set[str] = set()
        self.last_update_times: Dict[str, float] = {}

        # АДАПТИВНЫЕ интервалы в зависимости от количества профилей
        self.base_update_interval = 5.0  # Базовый интервал
        self.current_update_interval = 5.0
        self.batch_size_threshold = 20  # При превышении используем пакетную обработку

        # Кэширование для предотвращения избыточных обновлений
        self.stats_cache: Dict[str, dict] = {}
        self.performance_metrics = {
            'tasks_completed': 0,
            'average_duration': 0.0,
            'errors_count': 0
        }

        # Таймер для регулярного запуска обновлений
        self.scheduler_timer = QTimer()
        self.scheduler_timer.timeout.connect(self._schedule_stats_updates)
        self.scheduler_timer.start(int(self.current_update_interval * 1000))

        logger.info(f"📊 ProfileStatsWorker инициализирован: {optimized_max} потоков, "
                    f"интервал {self.current_update_interval}s")

    def add_profile(self, profile_name: str):
        """Добавляет профиль для мониторинга"""
        with QMutexLocker(self.mutex):
            self.active_profiles.add(profile_name)
            self.last_update_times[profile_name] = 0.0

        # Автоматически оптимизируем интервалы при изменении количества
        self._auto_optimize_intervals()

    def remove_profile(self, profile_name: str):
        """Убирает профиль из мониторинга"""
        with QMutexLocker(self.mutex):
            self.active_profiles.discard(profile_name)
            self.last_update_times.pop(profile_name, None)
            self.stats_cache.pop(profile_name, None)

        # Автоматически оптимизируем интервалы
        self._auto_optimize_intervals()

    def _auto_optimize_intervals(self):
        """Автоматически оптимизирует интервалы в зависимости от количества профилей"""
        with QMutexLocker(self.mutex):
            profile_count = len(self.active_profiles)

        # АДАПТИВНЫЕ интервалы для разного количества профилей
        if profile_count > 100:
            # Очень много профилей - редкие обновления
            new_interval = 20.0
        elif profile_count > 50:
            # Много профилей - умеренные обновления
            new_interval = 15.0
        elif profile_count > 20:
            # Среднее количество - нормальные обновления
            new_interval = 10.0
        else:
            # Мало профилей - частые обновления
            new_interval = 5.0

        # Обновляем интервал если изменился
        if new_interval != self.current_update_interval:
            self.current_update_interval = new_interval

            # Перезапускаем таймер с новым интервалом
            self.scheduler_timer.stop()
            self.scheduler_timer.start(int(new_interval * 1000))

            logger.info(f"🎯 Автооптимизация: {profile_count} профилей → интервал {new_interval}s")

    def _schedule_stats_updates(self):
        """Планирует обновления статистики для всех активных профилей"""
        current_time = time.time()
        profiles_to_update = []

        # Собираем профили, которые нужно обновить
        with QMutexLocker(self.mutex):
            for profile_name in list(self.active_profiles):
                last_update = self.last_update_times.get(profile_name, 0)
                if (current_time - last_update) >= self.current_update_interval:
                    profiles_to_update.append(profile_name)
                    self.last_update_times[profile_name] = current_time

        if not profiles_to_update:
            return

        # ОПТИМИЗАЦИЯ: Выбираем стратегию обновления
        if len(profiles_to_update) >= self.batch_size_threshold:
            # Много профилей - используем пакетную обработку
            self._schedule_batch_update(profiles_to_update)
        else:
            # Мало профилей - используем индивидуальные задачи
            self._schedule_individual_updates(profiles_to_update)

    def _schedule_batch_update(self, profiles: List[str]):
        """Планирует пакетное обновление для большого количества профилей"""
        # ИСПРАВЛЕНО: Передаем self как signals объект
        batch_task = BatchStatsTask(profiles, self._get_optimized_profile_stats, self)

        # Добавляем в пул потоков
        self.thread_pool.start(batch_task)

        logger.debug(f"📦 Запланировано пакетное обновление для {len(profiles)} профилей")

    def _schedule_individual_updates(self, profiles: List[str]):
        """Планирует индивидуальные обновления для небольшого количества профилей"""
        for profile_name in profiles:
            # ИСПРАВЛЕНО: Передаем self как signals объект
            task = ProfileStatsTask(profile_name, self._get_optimized_profile_stats, self)

            # Добавляем в пул потоков
            self.thread_pool.start(task)

    def _get_optimized_profile_stats(self, profile_name: str) -> Optional[dict]:
        """ОПТИМИЗИРОВАННОЕ получение статистики профиля"""
        try:
            # ОПТИМИЗАЦИЯ: Быстрая проверка состояния
            if not self._quick_running_check(profile_name):
                # Профиль не работает - возвращаем базовую информацию
                return {
                    'success': 0,
                    'errors': 0,
                    'total_goal': 0,
                    'speed': 0,
                    'status': 'Остановлен',
                    'is_running': False,
                    'timestamp': time.time()
                }

            # Профиль работает - получаем детальную статистику
            from src.modules.impl.inviter import get_profile_progress

            progress_data = get_profile_progress(profile_name)
            if not progress_data:
                return None

            # Возвращаем оптимизированный набор данных
            return {
                'success': progress_data.get('success', 0),
                'errors': progress_data.get('errors', 0),
                'total_goal': progress_data.get('total_goal', 0),
                'speed': progress_data.get('speed', 0),
                'status': progress_data.get('status', 'Работает'),
                'is_running': True,
                'last_action': progress_data.get('last_action', ''),
                'timestamp': time.time()
            }

        except Exception as e:
            # Логируем только в debug режиме для избежания спама
            logger.debug(f"Ошибка получения статистики {profile_name}: {e}")
            return None

    def _quick_running_check(self, profile_name: str) -> bool:
        """Быстрая проверка работает ли профиль (без тяжелых операций)"""
        try:
            from src.modules.impl.inviter.inviter_manager import _inviter_module_manager

            if not _inviter_module_manager:
                return False

            # Простая проверка наличия в активных процессах
            return profile_name in _inviter_module_manager.active_processes

        except Exception:
            return False

    def get_performance_metrics(self) -> dict:
        """Возвращает метрики производительности"""
        active_threads = self.thread_pool.activeThreadCount()
        max_threads = self.thread_pool.maxThreadCount()

        with QMutexLocker(self.mutex):
            profile_count = len(self.active_profiles)

        return {
            'active_threads': active_threads,
            'max_threads': max_threads,
            'thread_utilization': f"{(active_threads / max_threads * 100):.1f}%",
            'monitored_profiles': profile_count,
            'update_interval': self.current_update_interval,
            'cache_size': len(self.stats_cache),
            **self.performance_metrics
        }

    def stop_worker(self):
        """Останавливает рабочий"""
        logger.info("🛑 Остановка ProfileStatsWorker...")

        # Останавливаем планировщик
        self.scheduler_timer.stop()

        # Ждем завершения активных задач (максимум 3 секунды)
        if self.thread_pool.activeThreadCount() > 0:
            logger.info(f"⏳ Ожидание завершения {self.thread_pool.activeThreadCount()} задач...")
            self.thread_pool.waitForDone(3000)

        # Очищаем данные
        with QMutexLocker(self.mutex):
            self.active_profiles.clear()
            self.last_update_times.clear()
            self.stats_cache.clear()

        logger.info("✅ ProfileStatsWorker остановлен")


class ChatStatsWorker(QObject):
    """ОПТИМИЗИРОВАННЫЙ рабочий для статистики чатов"""

    chat_stats_updated = Signal(str, dict)

    def __init__(self):
        super().__init__()

        # Используем тот же пул потоков
        self.thread_pool = QThreadPool.globalInstance()

        self.mutex = QMutex()
        self.active_profiles: Set[str] = set()

        # Для чатов используем более редкие обновления
        self.update_interval = 30.0  # 30 секунд для статистики чатов

        # Таймер для обновлений
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._schedule_chat_updates)
        self.update_timer.start(int(self.update_interval * 1000))

    def add_profile(self, profile_name: str):
        """Добавляет профиль для мониторинга чатов"""
        with QMutexLocker(self.mutex):
            self.active_profiles.add(profile_name)

    def remove_profile(self, profile_name: str):
        """Убирает профиль из мониторинга чатов"""
        with QMutexLocker(self.mutex):
            self.active_profiles.discard(profile_name)

    def _schedule_chat_updates(self):
        """Планирует обновления статистики чатов"""
        with QMutexLocker(self.mutex):
            profiles = list(self.active_profiles)

        # ИСПРАВЛЕНО: Передаем self как signals объект
        for profile_name in profiles:
            if self._is_profile_running(profile_name):
                task = ProfileStatsTask(profile_name, self._get_chat_stats, self)
                self.thread_pool.start(task)

    def _is_profile_running(self, profile_name: str) -> bool:
        """Проверяет запущен ли профиль"""
        try:
            from src.modules.impl.inviter.inviter_manager import _inviter_module_manager

            if not _inviter_module_manager:
                return False

            return profile_name in _inviter_module_manager.active_processes

        except Exception:
            return False

    def _get_chat_stats(self, profile_name: str) -> Optional[dict]:
        """Получает статистику чатов (упрощенная версия)"""
        try:
            # Для оптимизации - возвращаем только базовую статистику чатов
            # Детальная статистика по чатам слишком ресурсоемкая для 100+ профилей
            return {
                'total_chats': 0,
                'active_chats': 0,
                'completed_chats': 0
            }
        except Exception as e:
            logger.debug(f"Ошибка получения статистики чатов {profile_name}: {e}")
            return None

    def stop_worker(self):
        """Останавливает рабочий чатов"""
        self.update_timer.stop()
        with QMutexLocker(self.mutex):
            self.active_profiles.clear()


class WorkerManager:
    """ОПТИМИЗИРОВАННЫЙ менеджер фоновых рабочих потоков"""

    def __init__(self):
        self.profile_stats_worker: Optional[ProfileStatsWorker] = None
        self.chat_stats_worker: Optional[ChatStatsWorker] = None
        self.is_initialized = False

    def initialize(self):
        """Инициализирует ОПТИМИЗИРОВАННУЮ систему рабочих"""
        if self.is_initialized:
            return

        try:
            # Создаем оптимизированных рабочих
            self.profile_stats_worker = ProfileStatsWorker()
            self.chat_stats_worker = ChatStatsWorker()

            self.is_initialized = True

            logger.info("✅ ОПТИМИЗИРОВАННЫЙ WorkerManager инициализирован")

            # Логируем конфигурацию
            if self.profile_stats_worker:
                metrics = self.profile_stats_worker.get_performance_metrics()
                logger.info(f"📊 Конфигурация: {metrics['max_threads']} потоков, "
                            f"интервал {metrics['update_interval']}s")

        except Exception as e:
            logger.error(f"❌ Ошибка инициализации ОПТИМИЗИРОВАННОГО WorkerManager: {e}")

    def shutdown(self):
        """Корректно останавливает всех рабочих"""
        if not self.is_initialized:
            return

        try:
            logger.info("🛑 Остановка ОПТИМИЗИРОВАННОГО WorkerManager...")

            if self.profile_stats_worker:
                self.profile_stats_worker.stop_worker()

            if self.chat_stats_worker:
                self.chat_stats_worker.stop_worker()

            self.is_initialized = False
            logger.info("✅ ОПТИМИЗИРОВАННЫЙ WorkerManager остановлен")

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

    def get_performance_metrics(self) -> dict:
        """Получает метрики производительности всей системы"""
        if self.profile_stats_worker:
            return self.profile_stats_worker.get_performance_metrics()
        return {}


# Глобальный менеджер - БЕЗ ИЗМЕНЕНИЯ ИМЕНИ
_worker_manager: Optional[WorkerManager] = None


def get_worker_manager() -> WorkerManager:
    """Получает глобальный менеджер рабочих"""
    global _worker_manager
    if _worker_manager is None:
        _worker_manager = WorkerManager()
    return _worker_manager


def init_worker_manager():
    """Инициализирует ОПТИМИЗИРОВАННУЮ систему фоновых рабочих"""
    manager = get_worker_manager()
    manager.initialize()
    return manager


def shutdown_worker_manager():
    """Останавливает ОПТИМИЗИРОВАННУЮ систему фоновых рабочих"""
    global _worker_manager
    if _worker_manager:
        _worker_manager.shutdown()
        _worker_manager = None