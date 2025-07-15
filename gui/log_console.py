# TeleCRM/gui/log_console.py

from pathlib import Path
import html

from PySide6.QtCore    import Qt, QObject, Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QFrame
from loguru            import logger


class LogEmitter(QObject):
    new_log = Signal(str)


class LogConsole(QWidget):
    LEVEL_COLORS = {
        "DEBUG":    "#3498db",
        "INFO":     "#2ecc71",
        "WARNING":  "#f1c40f",
        "ERROR":    "#e74c3c",
        "CRITICAL": "#c0392b"
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

        logger.add(
            self.emitter.new_log.emit,
            level="DEBUG",
            format="{time:HH:mm:ss}|{message}",
            colorize=False
        )

    def _append(self, text: str):
        # Разбор формата "HH:MM:SS|message"
        parts = text.split("|", 1)
        if len(parts) != 2:
            self.editor.append(text)
            return

        ts, msg = parts
        safe = html.escape(msg)
        html_line = (
            f"<span style='color:#777;'>{ts}</span> "
            f"<span style='color:#AAD4FF;'>{safe}</span>"
        )
        self.editor.append(html_line)
