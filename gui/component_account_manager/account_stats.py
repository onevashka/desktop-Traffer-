# TeleCRM/gui/components/account_stats.py - ОБНОВЛЕННАЯ ВЕРСИЯ
"""
Компонент статистики аккаунтов с кликабельными элементами
"""

from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QSizePolicy, QGraphicsOpacityEffect
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QRect, QEasingCurve, Signal
from PySide6.QtGui import QCursor


class AccountStatsWidget(QWidget):
    """Виджет отображения статистики аккаунтов с кликабельными элементами"""

    # Сигнал для клика по статистике
    stat_clicked = Signal(str)  # Передает status (ключ папки)

    def __init__(self, stats_data, category="traffic"):
        """
        stats_data: список кортежей (title, value, color, status_key)
        category: "traffic" или "sales"
        """
        super().__init__()
        self.setObjectName("AccountStatsWidget")
        self.stats_data = stats_data
        self.category = category

        # Основной layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 5, 0, 15)
        layout.setSpacing(20)

        # Создаем статистические блоки
        self.stat_boxes = []
        for i, (title, value, color, status_key) in enumerate(stats_data):
            box = self._create_stat_box(title, value, color, status_key, i)
            self.stat_boxes.append(box)
            layout.addWidget(box)

    def _create_stat_box(self, title, value, color, status_key, index):
        """Создает блок статистики"""
        box = QWidget()
        box.setObjectName("StatBox")
        box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        box.setFixedHeight(90)

        # Сохраняем данные для обработки клика
        box.status_key = status_key
        box.category = self.category
        box.index = index

        # Делаем кликабельным
        box.setCursor(QCursor(Qt.PointingHandCursor))
        box.mousePressEvent = lambda event, key=status_key: self._on_stat_click(key)

        # Layout блока
        layout = QHBoxLayout(box)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Индикатор цвета
        indicator = QWidget()
        indicator.setObjectName("StatIndicator")
        indicator.setFixedSize(5, 50)
        indicator.setStyleSheet(f"""
            QWidget#StatIndicator {{
                background: {color};
                border-radius: 3px;
            }}
        """)

        # Контейнер для текста
        text_container = QWidget()
        text_layout = QVBoxLayout(text_container)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(5)

        # Значение
        value_label = QLabel(value)
        value_label.setObjectName("StatValue")
        value_label.setStyleSheet(f"""
            QLabel#StatValue {{
                font-size: 26px;
                font-weight: 700;
                color: {color};
            }}
        """)

        # Заголовок
        title_label = QLabel(title)
        title_label.setObjectName("StatTitle")
        title_label.setStyleSheet("""
            QLabel#StatTitle {
                font-size: 13px;
                font-weight: 500;
                color: rgba(255, 255, 255, 0.8);
            }
        """)

        text_layout.addWidget(value_label)
        text_layout.addWidget(title_label)
        text_layout.addStretch()

        layout.addWidget(indicator)
        layout.addWidget(text_container)

        # Устанавливаем начальную прозрачность для анимации
        effect = QGraphicsOpacityEffect()
        effect.setOpacity(0.0)
        box.setGraphicsEffect(effect)

        return box

    def _on_stat_click(self, status_key):
        """Обработка клика по статистике"""
        self.stat_clicked.emit(status_key)

    def animate_appearance(self):
        """Анимирует появление статистических блоков"""
        for i, box in enumerate(self.stat_boxes):
            QTimer.singleShot(i * 150, lambda b=box: self._animate_stat_box(b))

    def _animate_stat_box(self, box):
        """Анимирует появление отдельного блока"""
        effect = box.graphicsEffect()
        if effect:
            # Анимация прозрачности
            self.opacity_animation = QPropertyAnimation(effect, b"opacity")
            self.opacity_animation.setDuration(600)
            self.opacity_animation.setStartValue(0.0)
            self.opacity_animation.setEndValue(1.0)
            self.opacity_animation.setEasingCurve(QEasingCurve.OutCubic)
            self.opacity_animation.start()

    def update_stat(self, index, new_value):
        """Обновляет значение статистики"""
        if 0 <= index < len(self.stat_boxes):
            box = self.stat_boxes[index]
            # Находим QLabel с значением внутри блока
            value_label = box.findChild(QLabel, "StatValue")
            if value_label:
                value_label.setText(new_value)

    def get_stats_data(self):
        """Возвращает текущие данные статистики"""
        return self.stats_data