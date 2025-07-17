"""
Менеджер уведомлений - управляет показом внутри главного окна (ИСПРАВЛЕННАЯ ВЕРСИЯ)
"""

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QObject, QTimer
from PySide6.QtGui import QScreen
from .notification_widget import NotificationWidget
from loguru import logger


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
            logger.warning("❌ Главное окно не установлено для NotificationManager")
            return None

        try:
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

        except Exception as e:
            logger.error(f"❌ Ошибка создания уведомления: {e}")
            return None

    def _calculate_position(self):
        """Вычисляет позицию для нового уведомления относительно главного окна"""
        if not self.main_window:
            # Fallback - показываем в правом верхнем углу экрана
            screen = QApplication.primaryScreen()
            screen_geometry = screen.availableGeometry()
            return screen_geometry.width() - 420, 20

        try:
            # Получаем геометрию главного окна
            main_rect = self.main_window.geometry()

            # ИСПРАВЛЕНО: Более надежный расчет позиции
            notification_width = 400

            # Позиция справа сверху относительно главного окна
            x = main_rect.width() - notification_width - self.margin_from_edge
            y = self.margin_from_edge

            # Сдвигаем вниз если есть другие уведомления
            for notification in self.active_notifications:
                if notification and not notification.is_closing:
                    y += notification.height() + self.notification_spacing

            # Преобразуем в глобальные координаты
            global_pos = self.main_window.mapToGlobal(self.main_window.rect().topLeft())

            # ИСПРАВЛЕНО: Проверяем границы экрана
            screen = QApplication.primaryScreen()
            screen_geometry = screen.availableGeometry()

            final_x = global_pos.x() + x
            final_y = global_pos.y() + y

            # Корректируем если выходит за пределы экрана
            if final_x + notification_width > screen_geometry.width():
                final_x = screen_geometry.width() - notification_width - 10

            if final_y + 100 > screen_geometry.height():  # 100 - высота уведомления
                final_y = screen_geometry.height() - 100 - 10

            return final_x, final_y

        except Exception as e:
            logger.error(f"❌ Ошибка расчета позиции уведомления: {e}")
            # Fallback позиция
            return 100, 100

    def _on_notification_closed(self, notification):
        """Обработка закрытия уведомления"""
        try:
            if notification in self.active_notifications:
                self.active_notifications.remove(notification)

            # Пересчитываем позиции оставшихся уведомлений
            self._reposition_notifications()
        except Exception as e:
            logger.error(f"❌ Ошибка при закрытии уведомления: {e}")

    def _reposition_notifications(self):
        """Пересчитывает позиции активных уведомлений"""
        if not self.main_window:
            return

        try:
            main_rect = self.main_window.geometry()
            global_pos = self.main_window.mapToGlobal(self.main_window.rect().topLeft())

            notification_width = 400
            x = main_rect.width() - notification_width - self.margin_from_edge
            y = self.margin_from_edge

            for notification in self.active_notifications:
                if notification and not notification.is_closing:
                    # Глобальные координаты для позиционирования
                    global_x = global_pos.x() + x
                    global_y = global_pos.y() + y

                    # ИСПРАВЛЕНО: Проверяем границы экрана
                    screen = QApplication.primaryScreen()
                    screen_geometry = screen.availableGeometry()

                    if global_x + notification_width > screen_geometry.width():
                        global_x = screen_geometry.width() - notification_width - 10

                    if global_y + 100 > screen_geometry.height():
                        global_y = screen_geometry.height() - 100 - 10

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

        except Exception as e:
            logger.error(f"❌ Ошибка пересчета позиций уведомлений: {e}")

    def clear_all(self):
        """Закрывает все активные уведомления"""
        try:
            for notification in self.active_notifications[:]:
                if notification and not notification.is_closing:
                    notification.animate_out()
        except Exception as e:
            logger.error(f"❌ Ошибка закрытия всех уведомлений: {e}")

    def update_positions(self):
        """Обновляет позиции всех уведомлений при изменении размера окна"""
        try:
            self._reposition_notifications()
        except Exception as e:
            logger.error(f"❌ Ошибка обновления позиций: {e}")


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
    try:
        manager = get_notification_manager()
        manager.set_main_window(main_window)
        logger.info("✅ NotificationManager инициализирован")
        return manager
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации NotificationManager: {e}")
        return None


# Удобные функции для быстрого использования
def show_success(title, message, duration=4000):
    """Показывает уведомление об успехе"""
    try:
        return get_notification_manager().show_success(title, message, duration)
    except Exception as e:
        logger.error(f"❌ Ошибка показа success уведомления: {e}")
        return None


def show_error(title, message, duration=6000):
    """Показывает уведомление об ошибке"""
    try:
        return get_notification_manager().show_error(title, message, duration)
    except Exception as e:
        logger.error(f"❌ Ошибка показа error уведомления: {e}")
        return None


def show_warning(title, message, duration=5000):
    """Показывает предупреждение"""
    try:
        return get_notification_manager().show_warning(title, message, duration)
    except Exception as e:
        logger.error(f"❌ Ошибка показа warning уведомления: {e}")
        return None


def show_info(title, message, duration=4000):
    """Показывает информационное уведомление"""
    try:
        return get_notification_manager().show_info(title, message, duration)
    except Exception as e:
        logger.error(f"❌ Ошибка показа info уведомления: {e}")
        return None