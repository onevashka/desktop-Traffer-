# desktop Traffer/core/paths.py
"""
Центральный менеджер путей для desktop Traffer
Простые переменные с путями к папкам и файлам
"""

import os
import sys
from pathlib import Path
from loguru import logger

# Получаем путь к исполняемому файлу (или к директории с main.py)
if getattr(sys, 'frozen', False):
    # Если запущен как exe файл
    BASE_PATH = Path(sys.executable).parent
else:
    # Если запущен как Python скрипт - берем папку где лежит main.py
    # Находим main.py через sys.argv[0] или текущую директорию
    if len(sys.argv) > 0 and sys.argv[0]:
        main_file = Path(sys.argv[0]).resolve()
        if main_file.name == '__main__.py':
            # Запущено через python -m main
            BASE_PATH = Path.cwd()
        else:
            BASE_PATH = main_file.parent
    else:
        BASE_PATH = Path.cwd()

#--------------- Для работы, Траффер ---------------
WORK_TRAFFER_FOLDER = BASE_PATH / "Для работы"
WORK_ACCOUNTS_TRAFFER_FOLDER = WORK_TRAFFER_FOLDER / "Аккаунты"
DEAD_TRAFFER_FOLDER = WORK_TRAFFER_FOLDER / "Мертвые"
FROZEN_TRAFFER_FOLDER = WORK_TRAFFER_FOLDER / "Замороженные"
INVALID_TRAFFER_FORMAT_FOLDER = WORK_TRAFFER_FOLDER / "Неверный формат"

#--------------- Продажи ---------------
WORK_SALES_FOLDER = BASE_PATH / "Продажи"
DEAD_SALES_FOLDER = WORK_SALES_FOLDER / "Мертвые"
FROZEN_SALES_FOLDER = WORK_SALES_FOLDER / "Замороженные"
INVALID_SALES_FORMAT_FOLDER = WORK_SALES_FOLDER / "Неверный формат"

READY_FOR_SALE_FOLDER = WORK_SALES_FOLDER / "Готовые для продажи"
MIDDLE_ACCOUNTS_FOLDER = WORK_SALES_FOLDER / "Средние"


# Подпапки в "Готовые для продажи"
WORK_ACCOUNTS_SALE_FOLDER = WORK_SALES_FOLDER / "Регистарция"
TDATA_FOLDER = READY_FOR_SALE_FOLDER / "Тдата"
SESSIONS_JSON_FOLDER = READY_FOR_SALE_FOLDER / "Сессии+json"

#----------------------------------------

# Файлы
PROXY_FILE = BASE_PATH / "прокси.txt"

# Список всех папок для создания
ALL_FOLDERS = [
    WORK_TRAFFER_FOLDER,
    WORK_SALES_FOLDER,
    DEAD_TRAFFER_FOLDER,
    FROZEN_TRAFFER_FOLDER,
    INVALID_TRAFFER_FORMAT_FOLDER,
    DEAD_SALES_FOLDER,
    FROZEN_SALES_FOLDER,
    INVALID_SALES_FORMAT_FOLDER,
    READY_FOR_SALE_FOLDER,
    MIDDLE_ACCOUNTS_FOLDER,
    TDATA_FOLDER,
    SESSIONS_JSON_FOLDER,
    WORK_ACCOUNTS_SALE_FOLDER,
    WORK_ACCOUNTS_TRAFFER_FOLDER
]

# Список всех файлов для создания
ALL_FILES = [
    PROXY_FILE
]


def ensure_folder_structure():
    """
    Проверить и создать структуру папок и файлов
    Вызывается при каждом запуске приложения
    """
    try:
        # Создаем папки
        for folder in ALL_FOLDERS:
            folder.mkdir(parents=True, exist_ok=True)

        # Создаем файлы если не существуют
        for file in ALL_FILES:
            if not file.exists():
                file.touch()
    except PermissionError as e:
        logger.error(f"Ошибка прав доступа: {e}")
        logger.error(f"Пытаемся создать в: {BASE_PATH}")
