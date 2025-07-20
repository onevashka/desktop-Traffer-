"""
Виджет уведомления - привязанный к главному окну (ИСПРАВЛЕННАЯ ВЕРСИЯ)
"""

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
    QGraphicsOpacityEffect, QGraphicsDropShadowEffect, QApplication
)
from PySide6.QtCore import (
    Qt, QPropertyAnimation, QEasingCurve, QTimer, QEvent,
    QRect, Signal, QParallelAnimationGroup, QSize
)
from PySide6.QtGui import QFont, QPixmap, QPainter, QColor, QScreen
from loguru import logger



class NotificationWidget(QWidget):
    """Современный виджет уведомления привязанный к главному окну"""

    # Сигналы
    clicked = Signal()
    closed = Signal()

    # Типы уведомлений
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"

    def __init__(self, title, message, notification_type=INFO, duration=4000, main_window=None):
        super().__init__(main_window)  # Устанавливаем главное окно как родителя

        self.notification_type = notification_type
        self.duration = duration
        self.is_closing = False
        self.main_window = main_window

        # ИСПРАВЛЕНО: Настройка размеров окна
        self.notification_width = 400
        self.notification_height = 100

        # Устанавливаем флаги для overlay поверх главного окна
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)  # Не активируем окно при показе

        # ИСПРАВЛЕНО: Более мягкая настройка размеров
        self.setMinimumSize(QSize(self.notification_width, self.notification_height))
        self.setMaximumSize(QSize(self.notification_width, self.notification_height))
        self.resize(self.notification_width, self.notification_height)

        # Создаем UI
        self._create_ui(title, message)
        self._setup_animations()
        self._apply_styles()

        # Отслеживаем изменения главного окна
        if main_window:
            main_window.installEventFilter(self)

        # Автозакрытие
        if duration > 0:
            QTimer.singleShot(duration, self.animate_out)

    def eventFilter(self, obj, event):
        """Отслеживаем события главного окна"""
        if obj == self.main_window:
            # ИСПРАВЛЕНО: Правильное обращение к типам событий
            if event.type() == QEvent.Type.Resize:
                # При изменении размера главного окна, обновляем позицию
                QTimer.singleShot(50, self._update_position_on_resize)
            elif event.type() == QEvent.Type.Move:
                # При перемещении главного окна, двигаем уведомление
                QTimer.singleShot(50, self._update_position_on_move)
            elif event.type() == QEvent.Type.Close:
                # Если главное окно закрывается, закрываем уведомление
                self.animate_out()
        return super().eventFilter(obj, event)

    def _update_position_on_resize(self):
        """Обновляет позицию при изменении размера главного окна"""
        if self.main_window and not self.is_closing:
            # Запрашиваем у менеджера пересчет позиций
            try:
                from .notification_manager import get_notification_manager
                manager = get_notification_manager()
                if manager:
                    manager.update_positions()
            except Exception as e:
                logger.error(f"Ошибка обновления позиций: {e}")

    def _update_position_on_move(self):
        """Обновляет позицию при перемещении главного окна"""
        if self.main_window and not self.is_closing:
            # Запрашиваем у менеджера пересчет позиций
            try:
                from .notification_manager import get_notification_manager
                manager = get_notification_manager()
                if manager:
                    manager.update_positions()
            except Exception as e:
                logger.error(f"Ошибка обновления позиций: {e}")

    def _create_ui(self, title, message):
        """Создает интерфейс уведомления"""
        # Основной контейнер
        self.container = QWidget()
        self.container.setObjectName("NotificationContainer")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.container)

        # Layout контейнера
        container_layout = QHBoxLayout(self.container)
        container_layout.setContentsMargins(20, 15, 20, 15)
        container_layout.setSpacing(15)

        # Иконка
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(24, 24)
        self.icon_label.setAlignment(Qt.AlignCenter)
        self._set_icon()

        # Текстовый контент
        text_widget = QWidget()
        text_layout = QVBoxLayout(text_widget)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(5)

        # Заголовок
        self.title_label = QLabel(title)
        self.title_label.setObjectName("NotificationTitle")

        # Сообщение
        self.message_label = QLabel(message)
        self.message_label.setObjectName("NotificationMessage")
        self.message_label.setWordWrap(True)

        text_layout.addWidget(self.title_label)
        text_layout.addWidget(self.message_label)

        # Кнопка закрытия
        self.close_button = QPushButton("×")
        self.close_button.setObjectName("NotificationCloseButton")
        self.close_button.setFixedSize(30, 30)
        self.close_button.clicked.connect(self.animate_out)

        # Сборка layout
        container_layout.addWidget(self.icon_label)
        container_layout.addWidget(text_widget, 1)
        container_layout.addWidget(self.close_button)

        # Тень
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setXOffset(0)
        shadow.setYOffset(5)
        shadow.setColor(QColor(0, 0, 0, 100))
        self.container.setGraphicsEffect(shadow)

    def _set_icon(self):
        """Устанавливает иконку в зависимости от типа"""
        icons = {
            self.SUCCESS: "✅",
            self.ERROR: "❌",
            self.WARNING: "⚠️",
            self.INFO: "ℹ️"
        }

        icon_text = icons.get(self.notification_type, "ℹ️")
        self.icon_label.setText(icon_text)
        self.icon_label.setStyleSheet("font-size: 20px;")

    def _apply_styles(self):
        """Применяет стили в зависимости от типа - УЛУЧШЕННАЯ ЧИТАЕМОСТЬ"""
        # Базовые стили с улучшенной читаемостью
        base_style = f"""
            QWidget#NotificationContainer {{
                background: rgba(5, 5, 5, 0.98);
                border: 2px solid rgba(255, 255, 255, 0.3);
                border-radius: 12px;
                backdrop-filter: blur(25px);
            }}

            QLabel#NotificationTitle {{
                color: #FFFFFF;
                font-size: 14px;
                font-weight: 700;
                margin: 0;
                padding: 4px 8px;
                text-shadow: 0 2px 4px rgba(0, 0, 0, 1.0);
                background: rgba(0, 0, 0, 0.5);
                border-radius: 4px;
            }}

            QLabel#NotificationMessage {{
                color: #FFFFFF;
                font-size: 12px;
                font-weight: 500;
                margin: 0;
                padding: 6px 8px;
                text-shadow: 0 1px 3px rgba(0, 0, 0, 1.0);
                background: rgba(0, 0, 0, 0.3);
                border-radius: 4px;
                line-height: 1.4;
            }}

            QPushButton#NotificationCloseButton {{
                background: rgba(255, 255, 255, 0.2);
                border: 1px solid rgba(255, 255, 255, 0.4);
                border-radius: 15px;
                color: #FFFFFF;
                font-size: 16px;
                font-weight: bold;
            }}

            QPushButton#NotificationCloseButton:hover {{
                background: rgba(255, 255, 255, 0.3);
                border: 1px solid rgba(255, 255, 255, 0.6);
            }}

            QPushButton#NotificationCloseButton:pressed {{
                background: rgba(255, 255, 255, 0.4);
            }}
        """

        # Цветовые схемы для разных типов с улучшенным контрастом
        type_styles = {
            self.SUCCESS: """
                QWidget#NotificationContainer {
                    border-left: 4px solid #10B981;
                    background: rgba(5, 40, 25, 0.98);
                    border: 2px solid rgba(16, 185, 129, 0.5);
                }
            """,
            self.ERROR: """
                QWidget#NotificationContainer {
                    border-left: 4px solid #EF4444;
                    background: rgba(40, 5, 5, 0.98);
                    border: 2px solid rgba(239, 68, 68, 0.5);
                }
            """,
            self.WARNING: """
                QWidget#NotificationContainer {
                    border-left: 4px solid #F59E0B;
                    background: rgba(40, 30, 5, 0.98);
                    border: 2px solid rgba(245, 158, 11, 0.5);
                }
            """,
            self.INFO: """
                QWidget#NotificationContainer {
                    border-left: 4px solid #3B82F6;
                    background: rgba(5, 20, 40, 0.98);
                    border: 2px solid rgba(59, 130, 246, 0.5);
                }
            """
        }

        # Применяем стили
        full_style = base_style + type_styles.get(self.notification_type, type_styles[self.INFO])
        self.setStyleSheet(full_style)

    def _setup_animations(self):
        """Настраивает анимации"""
        # Эффект прозрачности
        self.opacity_effect = QGraphicsOpacityEffect()
        self.opacity_effect.setOpacity(0.0)
        self.setGraphicsEffect(self.opacity_effect)

        # Анимации
        self.opacity_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.slide_animation = QPropertyAnimation(self, b"geometry")

        # Группа анимаций
        self.animation_group = QParallelAnimationGroup()
        self.animation_group.addAnimation(self.opacity_animation)
        self.animation_group.addAnimation(self.slide_animation)

    def _get_safe_position(self, x, y):
        """Получает безопасную позицию для уведомления в пределах экрана"""
        # Получаем геометрию экрана
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()

        # Корректируем позицию чтобы уведомление не выходило за пределы экрана
        safe_x = min(x, screen_geometry.width() - self.notification_width)
        safe_y = min(y, screen_geometry.height() - self.notification_height)

        # Минимальные отступы от краев
        safe_x = max(safe_x, 10)
        safe_y = max(safe_y, 10)

        return safe_x, safe_y

    def show_at_position(self, x, y):
        """Показывает уведомление в указанной позиции с анимацией"""
        # ИСПРАВЛЕНО: Получаем безопасную позицию
        safe_x, safe_y = self._get_safe_position(x, y)

        # Начальная позиция (справа за экраном)
        start_x = safe_x + 50
        start_rect = QRect(start_x, safe_y, self.notification_width, self.notification_height)
        end_rect = QRect(safe_x, safe_y, self.notification_width, self.notification_height)

        # ИСПРАВЛЕНО: Устанавливаем позицию через move() вместо setGeometry()
        self.move(start_x, safe_y)
        self.show()

        # Настройка анимации появления
        self.opacity_animation.setDuration(300)
        self.opacity_animation.setStartValue(0.0)
        self.opacity_animation.setEndValue(1.0)
        self.opacity_animation.setEasingCurve(QEasingCurve.OutCubic)

        self.slide_animation.setDuration(300)
        self.slide_animation.setStartValue(start_rect)
        self.slide_animation.setEndValue(end_rect)
        self.slide_animation.setEasingCurve(QEasingCurve.OutCubic)

        # Запускаем анимацию
        self.animation_group.start()

    def animate_out(self):
        """Анимация исчезновения"""
        if self.is_closing:
            return

        self.is_closing = True

        # Конечная позиция (вправо за экран)
        current_rect = self.geometry()
        end_rect = QRect(
            current_rect.x() + 50,
            current_rect.y(),
            current_rect.width(),
            current_rect.height()
        )

        # Настройка анимации исчезновения
        self.opacity_animation.setDuration(250)
        self.opacity_animation.setStartValue(1.0)
        self.opacity_animation.setEndValue(0.0)
        self.opacity_animation.setEasingCurve(QEasingCurve.InCubic)

        self.slide_animation.setDuration(250)
        self.slide_animation.setStartValue(current_rect)
        self.slide_animation.setEndValue(end_rect)
        self.slide_animation.setEasingCurve(QEasingCurve.InCubic)

        # После анимации закрываем виджет
        self.animation_group.finished.connect(self._on_animation_finished)
        self.animation_group.start()

    def _on_animation_finished(self):
        """Вызывается после завершения анимации"""
        self.closed.emit()
        self.close()
        self.deleteLater()

    def mousePressEvent(self, event):
        """Обработка клика по уведомлению"""
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def moveEvent(self, event):
        """ИСПРАВЛЕНО: Переопределяем moveEvent для отладки"""
        super().moveEvent(event)
        # Логируем только если есть проблемы с позиционированием
        # logger.debug(f"Notification moved to: {event.pos()}")

    def resizeEvent(self, event):
        """ИСПРАВЛЕНО: Переопределяем resizeEvent для отладки"""
        super().resizeEvent(event)
        # Логируем только если есть проблемы с размерами
        # logger.debug(f"Notification resized to: {event.size()}")

    def showEvent(self, event):
        """ИСПРАВЛЕНО: Переопределяем showEvent"""
        super().showEvent(event)
        # Убеждаемся что размеры корректны
        if self.size() != QSize(self.notification_width, self.notification_height):
            self.resize(self.notification_width, self.notification_height)