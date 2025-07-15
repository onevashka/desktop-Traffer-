# TeleCRM/gui/components/loading_animation.py
"""
Компонент анимации загрузки
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QRect, QEasingCurve


class LoadingAnimationWidget(QWidget):
    """Виджет анимации загрузки"""

    def __init__(self, loading_text="Загрузка..."):
        super().__init__()
        self.setObjectName("LoadingAnimationWidget")

        # Основной layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 20, 0, 20)
        layout.setSpacing(20)

        # Текст загрузки
        self.loading_label = QLabel(loading_text)
        self.loading_label.setObjectName("LoadingText")
        self.loading_label.setAlignment(Qt.AlignCenter)
        self.loading_label.setStyleSheet("""
            QLabel#LoadingText {
                font-size: 18px;
                font-weight: 500;
                color: rgba(255, 255, 255, 0.8);
            }
        """)

        # Контейнер прогресс бара
        progress_container = QWidget()
        progress_container.setFixedSize(300, 4)
        progress_container.setStyleSheet("""
            QWidget {
                background: rgba(255, 255, 255, 0.1);
                border-radius: 2px;
            }
        """)

        # Прогресс бар
        self.progress_bar = QWidget(progress_container)
        self.progress_bar.setObjectName("ProgressBar")
        self.progress_bar.setGeometry(0, 0, 0, 4)
        self.progress_bar.setStyleSheet("""
            QWidget#ProgressBar {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3B82F6, stop:1 #8B5CF6);
                border-radius: 2px;
            }
        """)

        layout.addStretch()
        layout.addWidget(self.loading_label, 0, Qt.AlignCenter)
        layout.addWidget(progress_container, 0, Qt.AlignCenter)
        layout.addStretch()

    def start_animation(self, callback=None):
        """Запускает анимацию загрузки"""
        # Анимация прогресс бара
        self.progress_animation = QPropertyAnimation(self.progress_bar, b"geometry")
        self.progress_animation.setDuration(2000)
        self.progress_animation.setStartValue(QRect(0, 0, 0, 4))
        self.progress_animation.setEndValue(QRect(0, 0, 300, 4))
        self.progress_animation.setEasingCurve(QEasingCurve.OutCubic)

        # Подключаем callback если передан
        if callback:
            self.progress_animation.finished.connect(callback)

        # Запускаем анимацию с небольшой задержкой
        QTimer.singleShot(300, self.progress_animation.start)

    def set_loading_text(self, text):
        """Изменяет текст загрузки"""
        self.loading_label.setText(text)