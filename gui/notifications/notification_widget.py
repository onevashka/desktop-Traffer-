"""
Виджет уведомления - СТРОГО ВНУТРИ окна приложения, НЕ ПОВЕРХ других окон
"""

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
    QGraphicsOpacityEffect, QGraphicsDropShadowEffect
)
from PySide6.QtCore import (
    Qt, QPropertyAnimation, QEasingCurve, QTimer,
    QRect, Signal, QParallelAnimationGroup, QSize
)
from PySide6.QtGui import QColor
from log_config import logger


class NotificationWidget(QWidget):
    """Уведомление как ВНУТРЕННИЙ элемент приложения (не отдельное окно)"""

    # Сигналы
    clicked = Signal()
    closed = Signal()

    # Типы уведомлений
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"

    def __init__(self, title, message, notification_type=INFO, duration=4000, parent=None):
        # ВАЖНО: Создаем как ОБЫЧНЫЙ виджет с родителем (не отдельное окно)
        super().__init__(parent)

        self.notification_type = notification_type
        self.duration = duration
        self.is_closing = False

        # Размеры
        self.notification_width = 380
        self.notification_height = 90

        # УБИРАЕМ все флаги окна - это будет обычный виджет
        self.setFixedSize(self.notification_width, self.notification_height)

        # Поднимаем виджет поверх других элементов родителя
        self.raise_()

        # Создаем UI
        self._create_ui(title, message)
        self._setup_animations()
        self._apply_solid_styles()

        # Автозакрытие
        if duration > 0:
            QTimer.singleShot(duration, self.animate_out)

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
        container_layout.setContentsMargins(12, 10, 12, 10)
        container_layout.setSpacing(10)

        # Иконка
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(20, 20)
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._set_icon()

        # Текстовый контент
        text_widget = QWidget()
        text_layout = QVBoxLayout(text_widget)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(3)

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
        self.close_button.setFixedSize(24, 24)
        self.close_button.clicked.connect(self.animate_out)

        # Сборка layout
        container_layout.addWidget(self.icon_label)
        container_layout.addWidget(text_widget, 1)
        container_layout.addWidget(self.close_button)

        # Тень
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(12)
        shadow.setXOffset(2)
        shadow.setYOffset(3)
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
        self.icon_label.setStyleSheet("font-size: 16px;")

    def _apply_solid_styles(self):
        """СТИЛИ для внутреннего виджета"""
        base_style = """
            QWidget#NotificationContainer {
                border-radius: 8px;
                border: 2px solid #FFFFFF;
            }

            QLabel#NotificationTitle {
                font-size: 12px;
                font-weight: 700;
                margin: 0;
                padding: 4px 8px;
                border-radius: 4px;
                color: #FFFFFF;
                text-shadow: 0 1px 2px rgba(0, 0, 0, 0.7);
            }

            QLabel#NotificationMessage {
                font-size: 10px;
                font-weight: 500;
                margin: 0;
                padding: 4px 8px;
                border-radius: 4px;
                color: #FFFFFF;
                text-shadow: 0 1px 1px rgba(0, 0, 0, 0.5);
                line-height: 1.2;
            }

            QPushButton#NotificationCloseButton {
                background: #FFFFFF;
                border: 1px solid #CCCCCC;
                border-radius: 12px;
                color: #333333;
                font-size: 12px;
                font-weight: bold;
            }

            QPushButton#NotificationCloseButton:hover {
                background: #F5F5F5;
                border: 1px solid #999999;
            }

            QPushButton#NotificationCloseButton:pressed {
                background: #E8E8E8;
            }
        """

        # ЯРКИЕ НЕПРОЗРАЧНЫЕ цвета
        type_styles = {
            self.SUCCESS: """
                QWidget#NotificationContainer {
                    background: #22C55E;
                    border-color: #16A34A;
                }
                QLabel#NotificationTitle {
                    background: #16A34A;
                }
                QLabel#NotificationMessage {
                    background: #059669;
                }
            """,
            self.ERROR: """
                QWidget#NotificationContainer {
                    background: #EF4444;
                    border-color: #DC2626;
                }
                QLabel#NotificationTitle {
                    background: #DC2626;
                }
                QLabel#NotificationMessage {
                    background: #B91C1C;
                }
            """,
            self.WARNING: """
                QWidget#NotificationContainer {
                    background: #F59E0B;
                    border-color: #D97706;
                }
                QLabel#NotificationTitle {
                    background: #D97706;
                }
                QLabel#NotificationMessage {
                    background: #B45309;
                }
            """,
            self.INFO: """
                QWidget#NotificationContainer {
                    background: #3B82F6;
                    border-color: #2563EB;
                }
                QLabel#NotificationTitle {
                    background: #2563EB;
                }
                QLabel#NotificationMessage {
                    background: #1D4ED8;
                }
            """
        }

        full_style = base_style + type_styles.get(self.notification_type, type_styles[self.INFO])
        self.setStyleSheet(full_style)

    def _setup_animations(self):
        """Настраивает анимации"""
        # Эффект прозрачности ТОЛЬКО для анимации
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

    def show_at_position(self, x, y):
        """Показывает уведомление в указанной позиции ВНУТРИ родителя"""
        # x, y - координаты относительно родительского виджета

        # Начальная позиция (справа за пределами родителя)
        start_x = x + 50
        start_rect = QRect(start_x, y, self.notification_width, self.notification_height)
        end_rect = QRect(x, y, self.notification_width, self.notification_height)

        # Устанавливаем начальную позицию
        self.setGeometry(start_rect)
        self.show()
        self.raise_()  # Поднимаем поверх других виджетов

        # Настройка анимации появления
        self.opacity_animation.setDuration(200)
        self.opacity_animation.setStartValue(0.0)
        self.opacity_animation.setEndValue(1.0)
        self.opacity_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

        self.slide_animation.setDuration(200)
        self.slide_animation.setStartValue(start_rect)
        self.slide_animation.setEndValue(end_rect)
        self.slide_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

        # Запускаем анимацию
        self.animation_group.start()

        logger.debug(f"📍 Внутреннее уведомление показано в позиции ({x}, {y})")

    def animate_out(self):
        """Анимация исчезновения"""
        if self.is_closing:
            return

        self.is_closing = True
        logger.debug("🔄 Начинаем анимацию закрытия внутреннего уведомления")

        # Конечная позиция (вправо за пределы родителя)
        current_rect = self.geometry()
        end_rect = QRect(
            current_rect.x() + 50,
            current_rect.y(),
            current_rect.width(),
            current_rect.height()
        )

        # Настройка анимации исчезновения
        self.opacity_animation.setDuration(150)
        self.opacity_animation.setStartValue(1.0)
        self.opacity_animation.setEndValue(0.0)
        self.opacity_animation.setEasingCurve(QEasingCurve.Type.InCubic)

        self.slide_animation.setDuration(150)
        self.slide_animation.setStartValue(current_rect)
        self.slide_animation.setEndValue(end_rect)
        self.slide_animation.setEasingCurve(QEasingCurve.Type.InCubic)

        # После анимации закрываем виджет
        self.animation_group.finished.connect(self._on_animation_finished)
        self.animation_group.start()

    def _on_animation_finished(self):
        """Вызывается после завершения анимации"""
        logger.debug("✅ Анимация внутреннего уведомления завершена")
        self.closed.emit()
        self.hide()
        self.deleteLater()

    def mousePressEvent(self, event):
        """Обработка клика по уведомлению"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def move_to_position(self, x, y):
        """Перемещает уведомление в новую позицию с анимацией"""
        if self.is_closing:
            return

        current_rect = self.geometry()
        new_rect = QRect(x, y, current_rect.width(), current_rect.height())

        # Простая анимация перемещения
        move_animation = QPropertyAnimation(self, b"geometry")
        move_animation.setDuration(150)
        move_animation.setStartValue(current_rect)
        move_animation.setEndValue(new_rect)
        move_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        move_animation.start()

        # Сохраняем ссылку чтобы анимация не была удалена
        self._move_animation = move_animation