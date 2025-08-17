# TeleCRM/gui/log_console.py

from pathlib import Path
import html

from PySide6.QtCore    import QObject, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QFrame
from loguru            import logger
from log_config import DEBUG_MODE

class LogEmitter(QObject):
    new_log = Signal(str)


class LogConsole(QWidget):
    LEVEL_COLORS = {
        "DEBUG": "#3498db",  # синий
        "INFO": "#FFFFFF",  # белый
        "SUCCESS": "#2ecc71",  # зелёный
        "WARNING": "#f1c40f",  # жёлтый
        "ERROR": "#e74c3c",  # красный
        "CRITICAL": "#c0392b"  # тёмно-красный
    }

    def __init__(self):
        super().__init__()

        # — Убираем только прозрачность, возвращаем нормальную рамку ОС —
        # (Удалены setWindowFlags и WA_TranslucentBackground)

        self.setWindowTitle("desktop Traffer — Консоль логов")
        self.resize(800, 300)

        # — Подгружаем внешний QSS для консоли —
        style_file = Path("styles/console.qss")
        if style_file.exists():
            self.setStyleSheet(style_file.read_text(encoding="utf-8"))

        # — Создаём QTextEdit для логов —
        self.editor = QTextEdit()
        self.editor.setReadOnly(True)
        self.editor.setAcceptRichText(True)

        font = QFont("Consolas", 10)  # или другой моноширинный шрифт
        font.setWeight(QFont.Weight.Normal)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.editor.setFont(font)

        # Принудительно применяем стили
        # Принудительно применяем стили
        self.editor.setStyleSheet("""
            QTextEdit {
                background-color: #000000;
                color: #e8e8e8;
                border: none;
                border-radius: 10px;
                padding: 30px 28px;
                font-family: "Consolas", "Monaco", "Courier New", monospace;
                font-size: 13px;
                font-weight: normal;
                line-height: 1.8em;
                letter-spacing: 0.2px;
            }

            QTextEdit p {
                margin-top: 8px;
                margin-bottom: 8px;
                margin-left: 0px;
                margin-right: 0px;
            }

            QTextEdit p:first-child {
                margin-top: 0px;
            }
        """)

        # — Обёртка с бордюром (скруглённый QFrame) —
        container = QFrame()
        container.setObjectName("MainFrame")
        container.setLayout(QVBoxLayout())
        container.layout().setContentsMargins(0, 0, 0, 0)
        container.layout().addWidget(self.editor)

        # — Основной layout с отступом под бордюр —
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.addWidget(container)

        # — Подключаем Loguru → Qt-сигнал —
        self.emitter = LogEmitter()
        self.emitter.new_log.connect(self._append)

        console_level = "DEBUG" if DEBUG_MODE else "INFO"
        logger.add(
            self.emitter.new_log.emit,
            level=console_level,
            # теперь в выводе будет и уровень между временем и сообщением
            format="{time:HH:mm:ss}|{level}|{message}",
            colorize=False
        )

    def _append(self, text: str):
        # Ожидаем текст формата "HH:MM:SS|LEVEL|message"
        parts = text.split("|", 2)
        if len(parts) != 3:
            # fallback на старый режим, если формат неожиданный
            self.editor.append(html.escape(text))
            return

        ts, level, msg = parts
        safe = html.escape(msg)

        # Подбираем цвет для уровня
        color = self.LEVEL_COLORS.get(level, "#AAD4FF")

        # ДОБАВЛЯЕМ ОТСТУПЫ ПРЯМО В HTML
        html_line = (
            f"<div style='margin-bottom: 8px;'>"  # Отступ снизу каждого лога
            f"<span style='color:#777;'>{ts}</span> "
            f"<span style='color:{color}; font-weight:bold;'>{safe}</span>"
            f"</div>"
        )
        self.editor.append(html_line)
