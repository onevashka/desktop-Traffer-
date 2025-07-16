"""
Система современных уведомлений - привязанных к главному окну
"""

from .notification_manager import (
    NotificationManager,
    get_notification_manager,
    init_notification_manager,
    show_success,
    show_error,
    show_warning,
    show_info
)
from .notification_widget import NotificationWidget

__all__ = [
    'NotificationManager',
    'NotificationWidget',
    'get_notification_manager',
    'init_notification_manager',
    'show_success',
    'show_error',
    'show_warning',
    'show_info'
]