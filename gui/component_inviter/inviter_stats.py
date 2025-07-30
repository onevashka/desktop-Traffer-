# gui/component_inviter/inviter_stats.py
"""
Компонент статистики инвайтера
"""

from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QSizePolicy, QGraphicsOpacityEffect
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QRect, QEasingCurve, Signal
from PySide6.QtGui import QCursor


class InviterStatsWidget(QWidget):
    """Виджет отображения статистики инвайтера"""

    # Сигнал для клика по статистике
    stat_clicked = Signal(str)  # Передает key статистики

    def __init__(self, stats_data):
        """
        stats_data: список кортежей (title, value, color, key)
        """
        super().__init__()
        self.setObjectName("InviterStatsWidget")
        self.stats_data = stats_data

        # Основной layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 5, 0, 15)
        layout.setSpacing(20)

        # Создаем статистические блоки
        self.stat_boxes = []
        for i, (title, value, color, key) in enumerate(stats_data):
            box = self._create_stat_box(title, value, color, key, i)
            self.stat_boxes.append(box)
            layout.addWidget(box)

    def _create_stat_box(self, title, value, color, key, index):
        """Создает блок статистики"""
        box = QWidget()
        box.setObjectName("InviterStatBox")
        box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        box.setFixedHeight(90)

        # Сохраняем данные для обработки клика
        box.stat_key = key
        box.index = index

        # Делаем кликабельным
        box.setCursor(QCursor(Qt.PointingHandCursor))
        box.mousePressEvent = lambda event, k=key: self._on_stat_click(k)

        # Layout блока
        layout = QHBoxLayout(box)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Индикатор цвета
        indicator = QWidget()
        indicator.setObjectName("InviterStatIndicator")
        indicator.setFixedSize(5, 50)
        indicator.setStyleSheet(f"""
            QWidget#InviterStatIndicator {{
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
        value_label.setObjectName("InviterStatValue")
        value_label.setStyleSheet(f"""
            QLabel#InviterStatValue {{
                font-size: 26px;
                font-weight: 700;
                color: {color};
            }}
        """)

        # Заголовок
        title_label = QLabel(title)
        title_label.setObjectName("InviterStatTitle")
        title_label.setStyleSheet("""
            QLabel#InviterStatTitle {
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

        # Стиль блока
        box.setStyleSheet("""
            QWidget#InviterStatBox {
                background: rgba(255, 255, 255, 0.04);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
                margin: 0;
            }
            QWidget#InviterStatBox:hover {
                background: rgba(255, 255, 255, 0.06);
                border: 1px solid rgba(59, 130, 246, 0.3);
                transform: translateY(-1px);
            }
        """)

        # Устанавливаем начальную прозрачность для анимации
        effect = QGraphicsOpacityEffect()
        effect.setOpacity(0.0)
        box.setGraphicsEffect(effect)

        return box

    def _on_stat_click(self, key):
        """Обработка клика по статистике"""
        self.stat_clicked.emit(key)

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
            value_label = box.findChild(QLabel, "InviterStatValue")
            if value_label:
                value_label.setText(new_value)

    def get_stats_data(self):
        """Возвращает текущие данные статистики"""
        return self.stats_data