import os

# Отключаем Qt предупреждения
os.environ['QT_LOGGING_RULES'] = '*.debug=false'

import sys
import asyncio
from pathlib import Path

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import qInstallMessageHandler
from qasync import QEventLoop

from paths import ensure_folder_structure
from gui.log_console import LogConsole
from gui.main_window import MainWindow
from src.accounts.manager import init_account_manager
from loguru import logger

log_console = None
main_win = None


def qt_message_handler(mode, context, message):
    if "Unknown property" not in message:
        print(f"Qt: {message}")


async def async_main():
    """Асинхронная инициализация приложения"""

    global log_console, main_win

    # 1. Создаем и показываем консоль логов
    log_console = LogConsole()
    log_console.show()
    logger.info("📋 Консоль логов открыта")

    await asyncio.sleep(1)

    # 2. Создаем структуру папок
    ensure_folder_structure()
    logger.info("📁 Структура папок создана")

    # 3. Создаем главное окно СНАЧАЛА
    main_win = MainWindow()
    main_win.show()
    logger.info("🖥️  Главное окно открыто")

    # 4. ТЕПЕРЬ инициализируем AccountManager (после создания окна)
    try:
        logger.info("🎯 Начинаем инициализацию AccountManager...")

        # Показываем уведомление о начале загрузки (теперь окно уже есть)
        from gui.notifications import show_info
        show_info("Инициализация", "Загружаем аккаунты...")

        await init_account_manager()
        logger.info("✅ AccountManager инициализирован с полной загрузкой аккаунтов")

        # Показываем уведомление об успешной загрузке
        from gui.notifications import show_success
        show_success("Загрузка завершена", "Аккаунты успешно загружены")

    except Exception as e:
        logger.error(f"❌ Ошибка инициализации AccountManager: {e}")

        # Показываем ошибку (окно уже есть)
        from gui.notifications import show_error
        show_error("Ошибка инициализации", f"Не удалось загрузить аккаунты: {e}")

    logger.info("🚀 Приложение desktop-Traffer готово к работе!")


def main():
    app = QApplication(sys.argv)
    qInstallMessageHandler(qt_message_handler)

    # Загружаем тему
    style_file = Path("gui/style/light.qss")
    if style_file.exists():
        app.setStyleSheet(style_file.read_text(encoding="utf-8"))

    # Настраиваем асинхронный event loop
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    # Запускаем асинхронную инициализацию
    with loop:
        loop.run_until_complete(async_main())
        loop.run_forever()


if __name__ == "__main__":
    main()