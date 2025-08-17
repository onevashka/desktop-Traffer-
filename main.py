# ============================================================================
# МАКСИМАЛЬНОЕ ОТКЛЮЧЕНИЕ ВСЕХ ПРЕДУПРЕЖДЕНИЙ И ОШИБОК + СКРЫТИЕ КОНСОЛИ
# ============================================================================

import warnings
import logging
import asyncio
import sys
import os

# СКРЫВАЕМ КОНСОЛЬНОЕ ОКНО В WINDOWS
'''if os.name == 'nt':  # Windows
    import ctypes
    from ctypes import wintypes

    # Получаем handle консольного окна
    kernel32 = ctypes.windll.kernel32
    user32 = ctypes.windll.user32

    # Константы для ShowWindow
    SW_HIDE = 0
    SW_SHOW = 5

    # Скрываем консоль
    console_window = kernel32.GetConsoleWindow()
    if console_window:
        user32.ShowWindow(console_window, SW_HIDE)'''

# 1. ОТКЛЮЧАЕМ ВСЕ WARNINGS
warnings.filterwarnings("ignore")
warnings.simplefilter("ignore")
os.environ['PYTHONWARNINGS'] = 'ignore'

# 2. ОТКЛЮЧАЕМ ASYNCIO ПОЛНОСТЬЮ
logging.getLogger('asyncio').setLevel(logging.CRITICAL + 100)
logging.getLogger('asyncio').disabled = True
logging.getLogger('asyncio').propagate = False

# 3. ОТКЛЮЧАЕМ TELETHON ПОЛНОСТЬЮ
telethon_loggers = [
    'telethon', 'telethon.network', 'telethon.client', 'telethon.network.mtprotosender',
    'telethon.network.connection', 'telethon.network.connection.connection',
    'telethon.client.updates', 'telethon.helpers'
]

for logger_name in telethon_loggers:
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.CRITICAL + 100)
    logger.disabled = True
    logger.propagate = False


# 4. ПЕРЕОПРЕДЕЛЯЕМ sys.stderr ДЛЯ ФИЛЬТРАЦИИ
class ErrorFilter:
    def __init__(self, original_stderr):
        self.original_stderr = original_stderr
        self.blocked_keywords = [
            'Exception ignored in:',
            'RuntimeError: Event loop is closed',
            'RuntimeError: coroutine ignored GeneratorExit',
            'Queue.get',
            'MTProtoSender',
            'Connection._send_loop',
            '_recv_loop',
            '_start_reconnect',
            'create_task',
            '_check_closed',
            'getter.cancel()',
            'GeneratorExit',
            'Task was destroyed but it is pending',
            'Task exception was never retrieved'
        ]

    def write(self, message):
        # Блокируем все сообщения, которые идут в stderr (консоль)
        # Они теперь не будут показываться нигде
        pass

    def flush(self):
        pass

    def __getattr__(self, name):
        return getattr(self.original_stderr, name)


# Применяем фильтр к stderr (полностью блокируем вывод в консоль)
#sys.stderr = ErrorFilter(sys.stderr)


# Также блокируем stdout если нужно (обычный print)
class StdoutFilter:
    def __init__(self, original_stdout):
        self.original_stdout = original_stdout

    def write(self, message):
        # Блокируем все print() которые идут в консоль
        pass

    def flush(self):
        pass

    def __getattr__(self, name):
        return getattr(self.original_stdout, name)


# Раскомментируй следующую строку, если хочешь заблокировать и обычные print()
#sys.stdout = StdoutFilter(sys.stdout)


# 5. ПОЛНОСТЬЮ МОЛЧАЛИВЫЙ ОБРАБОТЧИК ИСКЛЮЧЕНИЙ
def completely_silent_exception_handler(loop, context):
    pass


# 6. ПЕРЕОПРЕДЕЛЯЕМ EXCEPTHOOK
original_excepthook = sys.excepthook


def filtered_excepthook(exc_type, exc_value, exc_traceback):
    # Полностью блокируем вывод исключений в консоль
    pass


#sys.excepthook = filtered_excepthook


# 7. МОНКИ-ПАТЧ ДЛЯ ASYNCIO
def patch_asyncio():
    """Патчим asyncio для подавления ошибок"""

    # Патчим BaseEventLoop._check_closed
    original_check_closed = asyncio.BaseEventLoop._check_closed

    def silent_check_closed(self):
        try:
            return original_check_closed(self)
        except RuntimeError as e:
            if 'Event loop is closed' in str(e):
                return  # Игнорируем
            raise

    asyncio.BaseEventLoop._check_closed = silent_check_closed

    # Патчим call_soon
    original_call_soon = asyncio.BaseEventLoop.call_soon

    def silent_call_soon(self, callback, *args, **kwargs):
        try:
            return original_call_soon(self, callback, *args, **kwargs)
        except RuntimeError as e:
            if 'Event loop is closed' in str(e):
                return None  # Игнорируем
            raise

    asyncio.BaseEventLoop.call_soon = silent_call_soon

    # Патчим create_task
    original_create_task = asyncio.BaseEventLoop.create_task

    def silent_create_task(self, coro, **kwargs):
        try:
            return original_create_task(self, coro, **kwargs)
        except RuntimeError as e:
            if 'Event loop is closed' in str(e):
                return None  # Игнорируем
            raise

    asyncio.BaseEventLoop.create_task = silent_create_task


# Применяем патчи
patch_asyncio()


# 8. УСТАНАВЛИВАЕМ ОБРАБОТЧИКИ ДЛЯ ВСЕХ ВОЗМОЖНЫХ LOOP
def setup_silent_handlers():
    """Устанавливает молчаливые обработчики для всех loop"""
    try:
        # Для текущего loop
        loop = asyncio.get_event_loop()
        loop.set_exception_handler(completely_silent_exception_handler)
    except:
        pass

    try:
        # Для running loop если есть
        loop = asyncio.get_running_loop()
        loop.set_exception_handler(completely_silent_exception_handler)
    except:
        pass


setup_silent_handlers()

# ============================================================================
# ОСНОВНОЙ КОД ПРИЛОЖЕНИЯ (БЕЗ ИЗМЕНЕНИЙ)
# ============================================================================

import os

os.environ['QT_LOGGING_RULES'] = '*=false'
os.environ['QT_FATAL_WARNINGS'] = '0'
os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = ''

from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import qInstallMessageHandler
from qasync import QEventLoop

from paths import ensure_folder_structure
#from gui.log_console import LogConsole
from gui.main_window import MainWindow
from src.accounts.manager import init_account_manager
from src.proxies.manager import get_proxy_manager
from loguru import logger

#log_console = None
main_win = None


def qt_message_handler(mode, context, message):
    """Фильтруем Qt сообщения - теперь они не идут в консоль"""
    # Полностью блокируем вывод Qt сообщений
    pass


async def async_main():
    """Асинхронная инициализация приложения"""

    global log_console, main_win

    # Устанавливаем обработчик для текущего loop
    loop = asyncio.get_running_loop()
    loop.set_exception_handler(completely_silent_exception_handler)

    # 1. Создаем и показываем консоль логов
    #log_console = LogConsole()
    #log_console.show()
    #logger.info("📋 Консоль логов открыта")

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

    try:
        logger.info("🌐 Инициализация ProxyManager...")
        proxy_manager = get_proxy_manager()
        total_proxies = proxy_manager.get_total_proxies()

        if total_proxies > 0:
            logger.info(f"✅ ProxyManager готов. Прокси в файле: {total_proxies}")
        else:
            logger.warning("⚠️ Файл прокси пуст или не найден")
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации ProxyManager: {e}")

    try:
        logger.info("📨 Инициализация модуля инвайтера...")
        from src.modules.impl.inviter import init_inviter_module
        await init_inviter_module()
        logger.info("✅ Модуль инвайтера инициализирован")
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации модуля инвайтера: {e}")

    # 5. Создаем главное окно
    main_win = MainWindow()
    main_win.show()
    logger.info("🖥️  Главное окно открыто")

    # 6. Показываем уведомление
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

    # Устанавливаем молчаливый обработчик
    loop.set_exception_handler(completely_silent_exception_handler)

    # Запускаем приложение
    with loop:
        try:
            loop.run_until_complete(async_main())
            loop.run_forever()
        except KeyboardInterrupt:
            logger.info("Приложение закрыто пользователем")
        except Exception as e:
            # Не показываем ошибки вообще
            pass
        finally:
            # Максимально тихое закрытие
            try:
                pending = asyncio.all_tasks(loop)
                for task in pending:
                    task.cancel()

                if pending:
                    # Короткий таймаут для завершения задач
                    try:
                        loop.run_until_complete(asyncio.wait(pending, timeout=0.1))
                    except:
                        pass  # Игнорируем все ошибки закрытия
            except:
                pass  # Игнорируем все


if __name__ == "__main__":
    main()