"""
Менеджер уведомлений - управляет показом и позиционированием
"""

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QObject, QTimer
from .notification_widget import NotificationWidget


class NotificationManager(QObject):
    """Менеджер для отображения уведомлений"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.active_notifications = []
        self.notification_spacing = 10
        self.margin_from_edge = 20

    def show_success(self, title, message, duration=4000):
        """Показывает уведомление об успехе"""
        return self._show_notification(title, message, NotificationWidget.SUCCESS, duration)

    def show_error(self, title, message, duration=6000):
        """Показывает уведомление об ошибке"""
        return self._show_notification(title, message, NotificationWidget.ERROR, duration)

    def show_warning(self, title, message, duration=5000):
        """Показывает предупреждение"""
        return self._show_notification(title, message, NotificationWidget.WARNING, duration)

    def show_info(self, title, message, duration=4000):
        """Показывает информационное уведомление"""
        return self._show_notification(title, message, NotificationWidget.INFO, duration)

    def _show_notification(self, title, message, notification_type, duration):
        """Создает и показывает уведомление"""
        notification = NotificationWidget(title, message, notification_type, duration)
        notification.closed.connect(lambda: self._on_notification_closed(notification))

        # Вычисляем позицию
        x, y = self._calculate_position()

        # Добавляем в список активных
        self.active_notifications.append(notification)

        # Показываем
        notification.show_at_position(x, y)

        return notification

    def _calculate_position(self):
        """Вычисляет позицию для нового уведомления"""
        # Получаем размер экрана
        screen = QApplication.primaryScreen().geometry()

        # Позиция справа сверху
        x = screen.width() - 400 - self.margin_from_edge  # 400 = ширина уведомления
        y = self.margin_from_edge

        # Сдвигаем вниз если есть другие уведомления
        for notification in self.active_notifications:
            if notification and not notification.is_closing:
                y += notification.height() + self.notification_spacing

        return x, y

    def _on_notification_closed(self, notification):
        """Обработка закрытия уведомления"""
        if notification in self.active_notifications:
            self.active_notifications.remove(notification)

        # Пересчитываем позиции оставшихся уведомлений
        self._reposition_notifications()

    def _reposition_notifications(self):
        """Пересчитывает позиции активных уведомлений"""
        screen = QApplication.primaryScreen().geometry()
        x = screen.width() - 400 - self.margin_from_edge
        y = self.margin_from_edge

        for notification in self.active_notifications:
            if notification and not notification.is_closing:
                # Плавно перемещаем в новую позицию
                current_rect = notification.geometry()
                new_rect = current_rect
                new_rect.setY(y)

                # Простая анимация перемещения
                if hasattr(notification, 'slide_animation'):
                    notification.slide_animation.setDuration(200)
                    notification.slide_animation.setStartValue(current_rect)
                    notification.slide_animation.setEndValue(new_rect)
                    notification.slide_animation.start()
                else:
                    notification.setGeometry(new_rect)

                y += notification.height() + self.notification_spacing

    def clear_all(self):
        """Закрывает все активные уведомления"""
        for notification in self.active_notifications[:]:
            if notification and not notification.is_closing:
                notification.animate_out()


# Глобальный экземпляр менеджера
_notification_manager = None


def get_notification_manager():
    """Получает глобальный экземпляр менеджера уведомлений"""
    global _notification_manager
    if _notification_manager is None:
        _notification_manager = NotificationManager()
    return _notification_manager


# Удобные функции для быстрого использования
def show_success(title, message, duration=4000):
    """Показывает уведомление об успехе"""
    return get_notification_manager().show_success(title, message, duration)


def show_error(title, message, duration=6000):
    """Показывает уведомление об ошибке"""
    return get_notification_manager().show_error(title, message, duration)


def show_warning(title, message, duration=5000):
    """Показывает предупреждение"""
    return get_notification_manager().show_warning(title, message, duration)


def show_info(title, message, duration=4000):
    """Показывает информационное уведомление"""
    return get_notification_manager().show_info(title, message, duration)