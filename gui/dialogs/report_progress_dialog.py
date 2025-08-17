# gui/dialogs/report_progress_dialog.py
"""
Диалог прогресса для генерации отчетов по аккаунтам
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QTextEdit, QFrame
)
from PySide6.QtCore import Qt, QTimer, Signal, QThread
from PySide6.QtGui import QFont, QMovie
from loguru import logger


class ReportProgressDialog(QDialog):
    """Красивый диалог прогресса генерации отчета"""

    # Сигналы
    cancelled = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Генерация отчета по аккаунтам")
        self.setModal(True)
        self.setFixedSize(500, 400)

        self.is_cancelled = False
        self.current_stage = ""

        self._create_ui()
        self._apply_styles()

        # Таймер для обновления анимации
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self._update_animation)
        self.animation_timer.start(500)
        self.animation_frame = 0

    def _create_ui(self):
        """Создает интерфейс диалога"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # Заголовок
        header_layout = QHBoxLayout()

        self.icon_label = QLabel("📊")
        self.icon_label.setStyleSheet("font-size: 32px;")

        self.title_label = QLabel("Генерация отчета по аккаунтам")
        self.title_label.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: #FFFFFF;
            margin-left: 10px;
        """)

        header_layout.addWidget(self.icon_label)
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()

        layout.addLayout(header_layout)

        # Разделитель
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet("background: rgba(255, 255, 255, 0.2);")
        layout.addWidget(separator)

        # Статус
        self.status_label = QLabel("🔍 Сканирование папок аккаунтов...")
        self.status_label.setStyleSheet("""
            font-size: 14px;
            color: #10B981;
            font-weight: 600;
            padding: 10px;
            background: rgba(16, 185, 129, 0.1);
            border-radius: 6px;
            border: 1px solid rgba(16, 185, 129, 0.3);
        """)
        layout.addWidget(self.status_label)

        # Прогресс бар (неопределенный)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Неопределенный прогресс
        self.progress_bar.setFixedHeight(20)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid rgba(255, 255, 255, 0.2);
                border-radius: 10px;
                background: rgba(0, 0, 0, 0.3);
                text-align: center;
                color: #FFFFFF;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3B82F6, stop:0.5 #8B5CF6, stop:1 #EC4899);
                border-radius: 8px;
            }
        """)
        layout.addWidget(self.progress_bar)

        # Детали процесса
        details_label = QLabel("Детали процесса:")
        details_label.setStyleSheet("""
            font-size: 12px;
            color: rgba(255, 255, 255, 0.7);
            font-weight: 600;
            margin-top: 10px;
        """)
        layout.addWidget(details_label)

        self.details_text = QTextEdit()
        self.details_text.setFixedHeight(150)
        self.details_text.setReadOnly(True)
        self.details_text.setStyleSheet("""
            QTextEdit {
                background: rgba(0, 0, 0, 0.4);
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 6px;
                color: #FFFFFF;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 11px;
                padding: 8px;
            }
        """)
        layout.addWidget(self.details_text)

        # Кнопки
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        self.cancel_btn = QPushButton("Отмена")
        self.cancel_btn.setFixedSize(100, 35)
        self.cancel_btn.clicked.connect(self._on_cancel)
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background: #EF4444;
                border: 1px solid #DC2626;
                border-radius: 6px;
                color: #FFFFFF;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background: #DC2626;
            }
            QPushButton:pressed {
                background: #B91C1C;
            }
        """)

        buttons_layout.addWidget(self.cancel_btn)
        layout.addLayout(buttons_layout)

    def _apply_styles(self):
        """Применяет стили к диалогу"""
        self.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1F2937, stop:1 #111827);
                border: 2px solid #374151;
                border-radius: 12px;
            }
        """)

    def update_status(self, status_text: str, details: str = ""):
        """Обновляет статус процесса"""
        self.current_stage = status_text
        self.status_label.setText(f"🔄 {status_text}")

        if details:
            self.add_detail(details)

    def add_detail(self, detail_text: str):
        """Добавляет детали процесса"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")

        formatted_detail = f"[{timestamp}] {detail_text}"
        self.details_text.append(formatted_detail)

        # Автоскролл вниз
        scrollbar = self.details_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def set_progress_range(self, minimum: int, maximum: int):
        """Устанавливает диапазон прогресса"""
        self.progress_bar.setRange(minimum, maximum)

    def set_progress_value(self, value: int):
        """Устанавливает значение прогресса"""
        self.progress_bar.setValue(value)

    def set_indeterminate_progress(self):
        """Устанавливает неопределенный прогресс"""
        self.progress_bar.setRange(0, 0)

    def _update_animation(self):
        """Обновляет анимацию иконки"""
        if not self.is_cancelled:
            icons = ["📊", "📈", "📉", "📋"]
            self.icon_label.setText(icons[self.animation_frame % len(icons)])
            self.animation_frame += 1

    def _on_cancel(self):
        """Обработка отмены"""
        self.is_cancelled = True
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.setText("Отменяем...")

        self.status_label.setText("❌ Отмена процесса...")
        self.status_label.setStyleSheet("""
            font-size: 14px;
            color: #EF4444;
            font-weight: 600;
            padding: 10px;
            background: rgba(239, 68, 68, 0.1);
            border-radius: 6px;
            border: 1px solid rgba(239, 68, 68, 0.3);
        """)

        self.add_detail("Процесс отменен пользователем")
        self.cancelled.emit()

    def finish_success(self, file_path: str, stats: dict):
        """Завершение с успехом"""
        self.animation_timer.stop()
        self.icon_label.setText("✅")

        self.status_label.setText("🎉 Отчет успешно создан!")
        self.status_label.setStyleSheet("""
            font-size: 14px;
            color: #10B981;
            font-weight: 600;
            padding: 10px;
            background: rgba(16, 185, 129, 0.2);
            border-radius: 6px;
            border: 1px solid rgba(16, 185, 129, 0.5);
        """)

        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)

        self.add_detail(f"✅ Отчет сохранен: {file_path}")
        self.add_detail(f"📊 Всего аккаунтов: {stats.get('total_accounts', 0)}")
        self.add_detail(f"🎯 Общее количество инвайтов: {stats.get('total_invites', 0)}")

        self.cancel_btn.setText("Закрыть")
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background: #10B981;
                border: 1px solid #059669;
                border-radius: 6px;
                color: #FFFFFF;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background: #059669;
            }
        """)
        self.cancel_btn.setEnabled(True)
        self.cancel_btn.clicked.disconnect()
        self.cancel_btn.clicked.connect(self.accept)

    def finish_error(self, error_message: str):
        """Завершение с ошибкой"""
        self.animation_timer.stop()
        self.icon_label.setText("❌")

        self.status_label.setText("💥 Ошибка генерации отчета")
        self.status_label.setStyleSheet("""
            font-size: 14px;
            color: #EF4444;
            font-weight: 600;
            padding: 10px;
            background: rgba(239, 68, 68, 0.2);
            border-radius: 6px;
            border: 1px solid rgba(239, 68, 68, 0.5);
        """)

        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

        self.add_detail(f"❌ Ошибка: {error_message}")

        self.cancel_btn.setText("Закрыть")
        self.cancel_btn.setEnabled(True)
        self.cancel_btn.clicked.disconnect()
        self.cancel_btn.clicked.connect(self.reject)


def show_report_progress_dialog(parent=None):
    """Показывает диалог прогресса генерации отчета"""
    dialog = ReportProgressDialog(parent)
    return dialog