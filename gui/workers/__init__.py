# gui/workers/__init__.py
"""
Система фоновых рабочих потоков для предотвращения блокировки GUI
"""

from .background_workers import (
    ProfileStatsWorker,
    ChatStatsWorker,
    WorkerManager,
    get_worker_manager,
    init_worker_manager,
    shutdown_worker_manager
)

__all__ = [
    'ProfileStatsWorker',
    'ChatStatsWorker',
    'WorkerManager',
    'get_worker_manager',
    'init_worker_manager',
    'shutdown_worker_manager'
]