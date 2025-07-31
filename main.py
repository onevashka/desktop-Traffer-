import os

os.environ['QT_LOGGING_RULES'] = '*=false'  # Отключаем ВСЕ Qt логи
os.environ['QT_FATAL_WARNINGS'] = '0'       # Отключаем фатальные предупреждения
os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = ''  # Убираем лишние сообщения

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

    await asyncio.sleep(0.5)

    # 2. Создаем структуру папок
    ensure_folder_structure()
    logger.info("📁 Структура папок создана")

    # 3. Инициализируем AccountManager
    try:
        logger.info("🎯 Инициализация AccountManager...")
        await init_account_manager()
        logger.info("✅ AccountManager инициализирован")
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации AccountManager: {e}")

    # 4. НОВОЕ: Инициализируем модуль инвайтера
    try:
        logger.info("📨 Инициализация модуля инвайтера...")
        from src.modules.impl.inviter import init_inviter_module
        await init_inviter_module()
        logger.info("✅ Модуль инвайтера инициализирован")
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации модуля инвайтера: {e}")

    # 5. Создаем главное окно (когда все данные загружены)
    main_win = MainWindow()
    main_win.show()
    logger.info("🖥️  Главное окно открыто")

    # 6. Показываем уведомление о готовности
    await asyncio.sleep(0.5)
    try:
        from gui.notifications import show_success
        show_success(
            "Приложение готово",
            "🚀 desktop-Traffer готов к работе!\n"
            "📨 Модуль инвайтера активен\n"
            "👥 Менеджер аккаунтов готов"
        )
    except Exception as e:
        logger.error(f"❌ Ошибка показа уведомления: {e}")

    logger.info("🚀 Приложение desktop-Traffer полностью готово к работе!")


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