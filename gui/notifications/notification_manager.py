"""
Менеджер уведомлений - СТРОГО ВНУТРИ окна приложения
"""

from PySide6.QtCore import QObject, QTimer
from .notification_widget import NotificationWidget  # ОРИГИНАЛЬНОЕ ИМЯ
from log_config import logger


class NotificationManager(QObject):  # ОРИГИНАЛЬНОЕ ИМЯ
    """Менеджер для отображения уведомлений СТРОГО ВНУТРИ приложения"""

    def __init__(self, main_window=None, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.active_notifications = []
        self.notification_spacing = 10
        self.margin_from_edge = 15

    def set_main_window(self, main_window):
        """Устанавливает главное окно"""
        self.main_window = main_window
        logger.info("✅ Главное окно установлено - уведомления ВНУТРИ приложения")

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
        """Создает и показывает уведомление ВНУТРИ главного окна"""
        if not self.main_window:
            logger.warning("❌ Главное окно не установлено")
            return None

        try:
            # Создаем уведомление как ДОЧЕРНИЙ виджет главного окна
            notification = NotificationWidget(
                title, message, notification_type, duration, self.main_window
            )
            notification.closed.connect(lambda: self._on_notification_closed(notification))

            # Вычисляем позицию ВНУТРИ окна
            x, y = self._calculate_internal_position()

            # Добавляем в список ПОСЛЕ вычисления позиции
            self.active_notifications.append(notification)

            # Показываем в относительных координатах
            notification.show_at_position(x, y)

            logger.info(f"📨 Внутреннее уведомление '{title}' показано в ({x}, {y})")
            return notification

        except Exception as e:
            logger.error(f"❌ Ошибка создания внутреннего уведомления: {e}")
            return None

    def _calculate_internal_position(self):
        """Рассчитывает позицию ВНУТРИ главного окна"""
        try:
            if not self.main_window:
                return 10, 10

            # Получаем размеры главного окна
            window_width = self.main_window.width()
            window_height = self.main_window.height()

            notification_width = 380
            notification_height = 90

            # Позиция в правом верхнем углу ВНУТРИ окна
            x = window_width - notification_width - self.margin_from_edge
            y = self.margin_from_edge

            # Сдвигаем вниз для каждого уже показанного уведомления
            visible_count = len([n for n in self.active_notifications if n and not n.is_closing])
            y += visible_count * (notification_height + self.notification_spacing)

            # Проверяем что не выходим за пределы окна
            max_y = window_height - notification_height - self.margin_from_edge
            if y > max_y:
                y = max_y

            # Проверяем что не выходим за левый край
            if x < self.margin_from_edge:
                x = self.margin_from_edge

            logger.debug(f"📍 Позиция ВНУТРИ окна: ({x}, {y}), видимых: {visible_count}")
            return x, y

        except Exception as e:
            logger.error(f"❌ Ошибка расчета внутренней позиции: {e}")
            return 10, 10

    def _on_notification_closed(self, notification):
        """Обработка закрытия уведомления"""
        try:
            if notification in self.active_notifications:
                self.active_notifications.remove(notification)
                logger.debug(f"🗑️ Внутреннее уведомление удалено, осталось: {len(self.active_notifications)}")

            # Пересчитываем позиции оставшихся уведомлений
            if self.active_notifications:
                QTimer.singleShot(50, self._reposition_all_notifications)

        except Exception as e:
            logger.error(f"❌ Ошибка при закрытии внутреннего уведомления: {e}")

    def _reposition_all_notifications(self):
        """Пересчитывает позиции всех уведомлений ВНУТРИ окна"""
        try:
            if not self.main_window or not self.active_notifications:
                return

            window_width = self.main_window.width()
            window_height = self.main_window.height()

            notification_width = 380
            notification_height = 90

            # Базовая позиция
            base_x = window_width - notification_width - self.margin_from_edge
            base_y = self.margin_from_edge

            # Проверяем границы окна
            if base_x < self.margin_from_edge:
                base_x = self.margin_from_edge

            # Пересчитываем позицию для каждого уведомления
            current_y = base_y

            for i, notification in enumerate(self.active_notifications):
                if notification and not notification.is_closing:
                    # Проверяем границы по Y
                    max_y = window_height - notification_height - self.margin_from_edge
                    if current_y > max_y:
                        current_y = max_y

                    # Перемещаем уведомление
                    if hasattr(notification, 'move_to_position'):
                        notification.move_to_position(base_x, current_y)
                    else:
                        notification.move(base_x, current_y)

                    logger.debug(f"📍 Внутреннее уведомление {i} перемещено в ({base_x}, {current_y})")

                    # Увеличиваем Y для следующего уведомления
                    current_y += notification_height + self.notification_spacing

        except Exception as e:
            logger.error(f"❌ Ошибка пересчета внутренних позиций: {e}")

    def clear_all(self):
        """Закрывает все активные уведомления"""
        try:
            notifications_to_close = self.active_notifications[:]
            for notification in notifications_to_close:
                if notification and not notification.is_closing:
                    notification.animate_out()
            logger.info(f"🧹 Начато закрытие {len(notifications_to_close)} внутренних уведомлений")
        except Exception as e:
            logger.error(f"❌ Ошибка закрытия всех внутренних уведомлений: {e}")

    def update_positions(self):
        """Обновляет позиции при изменении размера окна"""
        try:
            self._reposition_all_notifications()
        except Exception as e:
            logger.error(f"❌ Ошибка обновления внутренних позиций: {e}")


# Глобальный экземпляр менеджера
_notification_manager = None


def get_notification_manager():
    """Получает глобальный экземпляр менеджера внутренних уведомлений"""
    global _notification_manager
    if _notification_manager is None:
        _notification_manager = NotificationManager()  # ИСПРАВЛЕНО: создаем ПРАВИЛЬНЫЙ класс
    return _notification_manager


def init_notification_manager(main_window):
    """Инициализирует менеджер внутренних уведомлений"""
    try:
        manager = get_notification_manager()
        manager.set_main_window(main_window)

        # ВАЖНО: Подключаем обновление позиций при изменении размера окна
        if hasattr(main_window, 'resizeEvent'):
            original_resize = main_window.resizeEvent

            def new_resize_event(event):
                original_resize(event)
                # Обновляем позиции уведомлений при изменении размера
                QTimer.singleShot(100, manager.update_positions)

            main_window.resizeEvent = new_resize_event

        logger.info("✅ NotificationManager инициализирован - уведомления ТОЛЬКО внутри приложения")
        return manager
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации NotificationManager: {e}")
        return None


# Удобные функции для быстрого использования
def show_success(title, message, duration=4000):
    """Показывает уведомление об успехе ВНУТРИ приложения"""
    try:
        result = get_notification_manager().show_success(title, message, duration)
        return result
    except Exception as e:
        logger.error(f"❌ Ошибка показа внутреннего success уведомления: {e}")
        return None


def show_error(title, message, duration=6000):
    """Показывает уведомление об ошибке ВНУТРИ приложения"""
    try:
        result = get_notification_manager().show_error(title, message, duration)
        return result
    except Exception as e:
        logger.error(f"❌ Ошибка показа внутреннего error уведомления: {e}")
        return None


def show_warning(title, message, duration=5000):
    """Показывает предупреждение ВНУТРИ приложения"""
    try:
        result = get_notification_manager().show_warning(title, message, duration)
        return result
    except Exception as e:
        logger.error(f"❌ Ошибка показа внутреннего warning уведомления: {e}")
        return None


def show_info(title, message, duration=4000):
    """Показывает информационное уведомление ВНУТРИ приложения"""
    try:
        result = get_notification_manager().show_info(title, message, duration)
        return result
    except Exception as e:
        logger.error(f"❌ Ошибка показа внутреннего info уведомления: {e}")
        return None