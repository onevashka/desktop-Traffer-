import sys
import asyncio
from pathlib import Path

from PySide6.QtWidgets import QApplication
from qasync import QEventLoop

from paths import ensure_folder_structure
from gui.log_console import LogConsole   # ← ИМПОРТИРУЕМ раньше
from gui.main_window import MainWindow

def main():
    ensure_folder_structure()

    app = QApplication(sys.argv)

    # ─── Загружаем тему ───
    style_file = Path("gui/style/light.qss")
    if style_file.exists():
        app.setStyleSheet(style_file.read_text(encoding="utf-8"))

    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    # ─── Создаём и показываем ЛОГ-КОНСОЛЬ ПЕРВОЙ! ───
    log_console = LogConsole()
    log_console.show()

    # ─── Только теперь создаём основное окно ───
    main_win = MainWindow()
    main_win.show()

    with loop:
        loop.run_forever()

if __name__ == "__main__":
    main()
