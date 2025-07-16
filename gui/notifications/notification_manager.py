"""
Менеджер уведомлений - управляет показом внутри главного окна
"""

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QObject, QTimer
from .notification_widget import NotificationWidget


class NotificationManager(QObject):
    """Менеджер для отображения уведомлений внутри главного окна"""

    def __init__(self, main_window=None, parent=None):
        super().__init__(parent)
        self.main_window = main_window  # Ссылка на главное окно
        self.active_notifications = []
        self.notification_spacing = 10
        self.margin_from_edge = 20

    def set_main_window(self, main_window):
        """Устанавливает главное окно для привязки уведомлений"""
        self.main_window = main_window

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
        """Создает и показывает уведомление внутри главного окна"""
        if not self.main_window:
            print("❌ Главное окно не установлено для NotificationManager")
            return None

        # Создаем уведомление с главным окном как родителем
        notification = NotificationWidget(title, message, notification_type, duration, self.main_window)
        notification.closed.connect(lambda: self._on_notification_closed(notification))

        # Вычисляем позицию относительно главного окна
        x, y = self._calculate_position()

        # Добавляем в список активных
        self.active_notifications.append(notification)

        # Показываем
        notification.show_at_position(x, y)

        return notification

    def _calculate_position(self):
        """Вычисляет позицию для нового уведомления относительно главного окна"""
        if not self.main_window:
            return 0, 0

        # Получаем геометрию главного окна
        main_rect = self.main_window.geometry()

        # Позиция справа сверху относительно главного окна
        x = main_rect.width() - 400 - self.margin_from_edge  # 400 = ширина уведомления
        y = self.margin_from_edge

        # Сдвигаем вниз если есть другие уведомления
        for notification in self.active_notifications:
            if notification and not notification.is_closing:
                y += notification.height() + self.notification_spacing

        # Преобразуем в глобальные координаты
        global_pos = self.main_window.mapToGlobal(self.main_window.rect().topLeft())
        return global_pos.x() + x, global_pos.y() + y

    def _on_notification_closed(self, notification):
        """Обработка закрытия уведомления"""
        if notification in self.active_notifications:
            self.active_notifications.remove(notification)

        # Пересчитываем позиции оставшихся уведомлений
        self._reposition_notifications()

    def _reposition_notifications(self):
        """Пересчитывает позиции активных уведомлений"""
        if not self.main_window:
            return

        main_rect = self.main_window.geometry()
        global_pos = self.main_window.mapToGlobal(self.main_window.rect().topLeft())

        x = main_rect.width() - 400 - self.margin_from_edge
        y = self.margin_from_edge

        for notification in self.active_notifications:
            if notification and not notification.is_closing:
                # Глобальные координаты для позиционирования
                global_x = global_pos.x() + x
                global_y = global_pos.y() + y

                # Плавно перемещаем в новую позицию
                current_rect = notification.geometry()
                new_rect = current_rect
                new_rect.moveTo(global_x, global_y)

                # Простая анимация перемещения
                if hasattr(notification, 'slide_animation'):
                    notification.slide_animation.setDuration(200)
                    notification.slide_animation.setStartValue(current_rect)
                    notification.slide_animation.setEndValue(new_rect)
                    notification.slide_animation.start()
                else:
                    notification.move(global_x, global_y)

                y += notification.height() + self.notification_spacing

    def clear_all(self):
        """Закрывает все активные уведомления"""
        for notification in self.active_notifications[:]:
            if notification and not notification.is_closing:
                notification.animate_out()

    def update_positions(self):
        """Обновляет позиции всех уведомлений при изменении размера окна"""
        self._reposition_notifications()


# Глобальный экземпляр менеджера
_notification_manager = None


def get_notification_manager():
    """Получает глобальный экземпляр менеджера уведомлений"""
    global _notification_manager
    if _notification_manager is None:
        _notification_manager = NotificationManager()
    return _notification_manager


def init_notification_manager(main_window):
    """Инициализирует менеджер уведомлений с главным окном"""
    manager = get_notification_manager()
    manager.set_main_window(main_window)
    return manager


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