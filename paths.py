# TeleCRM/core/paths.py
"""
Центральный менеджер путей для TeleCRM
Простые переменные с путями к папкам и файлам
"""

import os
import sys
from pathlib import Path

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

# Главная рабочая папка рядом с exe/проектом
WORK_FOLDER = BASE_PATH / "Для работы"

# Основные папки для аккаунтов
DEAD_FOLDER = BASE_PATH / "Мертвые"
FROZEN_FOLDER = BASE_PATH / "Замороженные"
INVALID_FORMAT_FOLDER = BASE_PATH / "Неверный формат"
READY_FOR_SALE_FOLDER = BASE_PATH / "Готовые для продажи"

# Подпапки в "Готовые для продажи"
TDATA_FOLDER = READY_FOR_SALE_FOLDER / "Тдата"
SESSIONS_JSON_FOLDER = READY_FOR_SALE_FOLDER / "Сессии+json"

# Файлы
PROXY_FILE = BASE_PATH / "прокси.txt"

# Список всех папок для создания
ALL_FOLDERS = [
    WORK_FOLDER,
    DEAD_FOLDER,
    FROZEN_FOLDER,
    INVALID_FORMAT_FOLDER,
    READY_FOR_SALE_FOLDER,
    TDATA_FOLDER,
    SESSIONS_JSON_FOLDER
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
        print(f"Ошибка прав доступа: {e}")
        print(f"Пытаемся создать в: {BASE_PATH}")


if __name__ == "__main__":
    print(f"Base path: {BASE_PATH}")
    print(f"Work folder: {WORK_FOLDER}")
    ensure_folder_structure()