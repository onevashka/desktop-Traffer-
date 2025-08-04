# paths.py - ОБНОВЛЕННАЯ ВЕРСИЯ с новой структурой
"""
Центральный менеджер путей для desktop Traffer
Обновлено для поддержки новой логики главных админов
"""

import os
import sys
from pathlib import Path
from loguru import logger
from typing import List, Dict

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

# --------------- Для работы, Траффер ---------------
WORK_TRAFFER_FOLDER = BASE_PATH / "Для работы"
WORK_ACCOUNTS_TRAFFER_FOLDER = WORK_TRAFFER_FOLDER / "Аккаунты"
DEAD_TRAFFER_FOLDER = WORK_TRAFFER_FOLDER / "Мертвые"
FROZEN_TRAFFER_FOLDER = WORK_TRAFFER_FOLDER / "Замороженные"
INVALID_TRAFFER_FORMAT_FOLDER = WORK_TRAFFER_FOLDER / "Неверный формат"

# --------------- Инвайтер --------------------------
WORK_INVITER_FOLDER = WORK_TRAFFER_FOLDER / "Инвайт"

# УСТАРЕВШАЯ ПАПКА - оставляем для совместимости, но больше не используется
BOT_HOLDERS_FOLDER = WORK_INVITER_FOLDER / "Держатели_ботов"

# --------------- Продажи ---------------
WORK_SALES_FOLDER = BASE_PATH / "Продажи"
DEAD_SALES_FOLDER = WORK_SALES_FOLDER / "Мертвые"
FROZEN_SALES_FOLDER = WORK_SALES_FOLDER / "Замороженные"
INVALID_SALES_FORMAT_FOLDER = WORK_SALES_FOLDER / "Неверный формат"

READY_FOR_SALE_FOLDER = WORK_SALES_FOLDER / "Готовые для продажи"
MIDDLE_ACCOUNTS_FOLDER = WORK_SALES_FOLDER / "Средние"

# Подпапки в "Готовые для продажи"
WORK_ACCOUNTS_SALE_FOLDER = WORK_SALES_FOLDER / "Регистрация"
TDATA_FOLDER = READY_FOR_SALE_FOLDER / "Тдата"
SESSIONS_JSON_FOLDER = READY_FOR_SALE_FOLDER / "Сессии+json"

# ----------------------------------------

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
    WORK_ACCOUNTS_TRAFFER_FOLDER,
    WORK_INVITER_FOLDER,
    BOT_HOLDERS_FOLDER  # Оставляем для совместимости
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


def get_profile_folder(profile_name: str) -> Path:
    """
    НОВАЯ ФУНКЦИЯ: Получает путь к папке конкретного профиля

    Args:
        profile_name: Имя профиля

    Returns:
        Path: Путь к папке профиля
    """
    return WORK_INVITER_FOLDER / profile_name


def get_profile_admins_folder(profile_name: str) -> Path:
    """
    НОВАЯ ФУНКЦИЯ: Получает путь к папке админов профиля

    Args:
        profile_name: Имя профиля

    Returns:
        Path: Путь к папке админов профиля ([Профиль]/Админы/)
    """
    profile_folder = get_profile_folder(profile_name)
    admins_folder = profile_folder / "Админы"

    # Создаем папку если не существует
    admins_folder.mkdir(parents=True, exist_ok=True)

    return admins_folder


def get_profile_bot_token_file(profile_name: str) -> Path:
    """
    НОВАЯ ФУНКЦИЯ: Получает путь к файлу токена бота профиля

    Args:
        profile_name: Имя профиля

    Returns:
        Path: Путь к файлу токена ([Профиль]/bot_token.txt)
    """
    profile_folder = get_profile_folder(profile_name)
    return profile_folder / "bot_token.txt"


def get_profile_reports_folder(profile_name: str) -> Path:
    """
    НОВАЯ ФУНКЦИЯ: Получает путь к папке отчетов профиля

    Args:
        profile_name: Имя профиля

    Returns:
        Path: Путь к папке отчетов ([Профиль]/Отчеты/)
    """
    profile_folder = get_profile_folder(profile_name)
    reports_folder = profile_folder / "Отчеты"

    # Создаем папку если не существует
    reports_folder.mkdir(parents=True, exist_ok=True)

    return reports_folder


def ensure_profile_structure(profile_name: str):
    """
    НОВАЯ ФУНКЦИЯ: Обеспечивает создание полной структуры папок профиля

    Args:
        profile_name: Имя профиля
    """
    try:
        profile_folder = get_profile_folder(profile_name)

        # Создаем основную папку профиля
        profile_folder.mkdir(parents=True, exist_ok=True)

        # Создаем подпапки
        admins_folder = get_profile_admins_folder(profile_name)
        reports_folder = get_profile_reports_folder(profile_name)

        # Создаем файлы если не существуют
        files_to_create = [
            profile_folder / "База юзеров.txt",
            profile_folder / "База чатов.txt",
            profile_folder / "config.json"
        ]

        for file_path in files_to_create:
            if not file_path.exists():
                file_path.touch()

        logger.info(f"✅ Структура профиля {profile_name} обеспечена")
        logger.debug(f"   📁 Папка профиля: {profile_folder}")
        logger.debug(f"   👑 Папка админов: {admins_folder}")
        logger.debug(f"   📊 Папка отчетов: {reports_folder}")

    except Exception as e:
        logger.error(f"❌ Ошибка создания структуры профиля {profile_name}: {e}")


def migrate_from_old_bot_holders():
    """
    НОВАЯ ФУНКЦИЯ: Миграция из старой структуры (Держатели_ботов) в новую
    Эта функция поможет пользователям перейти на новую структуру
    """
    try:
        # Проверяем есть ли старая папка
        if not BOT_HOLDERS_FOLDER.exists():
            logger.info("📦 Старая папка держателей ботов не найдена, миграция не нужна")
            return

        # Проверяем есть ли файлы в старой папке
        session_files = list(BOT_HOLDERS_FOLDER.glob("*.session"))

        if not session_files:
            logger.info("📦 Старая папка держателей ботов пуста, миграция не нужна")
            return

        logger.info(f"🔄 Начинаем миграцию {len(session_files)} аккаунтов из старой структуры")

        # Показываем пользователю информацию о миграции
        logger.warning("=" * 60)
        logger.warning("🔄 МИГРАЦИЯ К НОВОЙ СТРУКТУРЕ")
        logger.warning("=" * 60)
        logger.warning(f"Найдено {len(session_files)} держателей ботов в старой папке")
        logger.warning("Для продолжения работы их нужно будет переназначить в профилях")
        logger.warning("Старые файлы остаются в папке 'Держатели_ботов' для безопасности")
        logger.warning("=" * 60)

        # Оставляем файлы в старой папке для безопасности
        # Пользователь сам решит что с ними делать

        return True

    except Exception as e:
        logger.error(f"❌ Ошибка миграции: {e}")
        return False


def get_all_profile_names() -> List[str]:
    """
    НОВАЯ ФУНКЦИЯ: Получает список всех профилей

    Returns:
        List[str]: Список имен профилей
    """
    try:
        if not WORK_INVITER_FOLDER.exists():
            return []

        profiles = []
        for item in WORK_INVITER_FOLDER.iterdir():
            if item.is_dir() and item.name != "Держатели_ботов":  # Исключаем старую папку
                # Проверяем что это папка профиля (есть config.json)
                config_file = item / "config.json"
                if config_file.exists():
                    profiles.append(item.name)

        return profiles

    except Exception as e:
        logger.error(f"❌ Ошибка получения списка профилей: {e}")
        return []


def validate_profile_structure(profile_name: str) -> Dict[str, any]:
    """
    НОВАЯ ФУНКЦИЯ: Валидирует структуру профиля

    Args:
        profile_name: Имя профиля

    Returns:
        Dict: Результат валидации с ошибками и предупреждениями
    """
    try:
        errors = []
        warnings = []
        info = []

        profile_folder = get_profile_folder(profile_name)

        # Проверяем основную папку
        if not profile_folder.exists():
            errors.append(f"Папка профиля не существует: {profile_folder}")
            return {"errors": errors, "warnings": warnings, "info": info}

        # Проверяем обязательные файлы
        required_files = [
            ("config.json", "Файл конфигурации"),
            ("База юзеров.txt", "База пользователей"),
            ("База чатов.txt", "База чатов")
        ]

        for filename, description in required_files:
            file_path = profile_folder / filename
            if not file_path.exists():
                warnings.append(f"{description} отсутствует: {filename}")
            elif file_path.stat().st_size == 0:
                warnings.append(f"{description} пустой: {filename}")
            else:
                info.append(f"{description} в порядке")

        # Проверяем папку админов
        admins_folder = get_profile_admins_folder(profile_name)
        admin_sessions = list(admins_folder.glob("*.session"))

        if admin_sessions:
            info.append(f"Главных админов: {len(admin_sessions)}")

            # Проверяем парность session/json файлов
            for session_file in admin_sessions:
                json_file = session_file.with_suffix(".json")
                if not json_file.exists():
                    warnings.append(f"Отсутствует JSON для админа: {session_file.stem}")
        else:
            warnings.append("Не назначены главные админы")

        # Проверяем токен бота
        token_file = get_profile_bot_token_file(profile_name)
        if token_file.exists() and token_file.stat().st_size > 0:
            info.append("Токен бота настроен")
        else:
            warnings.append("Токен бота не настроен")

        # Проверяем папку отчетов
        reports_folder = get_profile_reports_folder(profile_name)
        if reports_folder.exists():
            info.append("Папка отчетов создана")

        return {
            "errors": errors,
            "warnings": warnings,
            "info": info
        }

    except Exception as e:
        logger.error(f"❌ Ошибка валидации профиля {profile_name}: {e}")
        return {
            "errors": [f"Ошибка валидации: {e}"],
            "warnings": [],
            "info": []
        }


# НОВЫЕ УТИЛИТЫ для работы с главными админами

def get_main_admins_list(profile_name: str) -> List[str]:
    """
    Получает список главных админов профиля

    Args:
        profile_name: Имя профиля

    Returns:
        List[str]: Список имен главных админов
    """
    try:
        admins_folder = get_profile_admins_folder(profile_name)

        admins = []
        for session_file in admins_folder.glob("*.session"):
            # Проверяем что есть соответствующий JSON
            json_file = session_file.with_suffix(".json")
            if json_file.exists():
                admins.append(session_file.stem)

        return admins

    except Exception as e:
        logger.error(f"❌ Ошибка получения списка админов для {profile_name}: {e}")
        return []


def is_main_admin(profile_name: str, account_name: str) -> bool:
    """
    Проверяет является ли аккаунт главным админом профиля

    Args:
        profile_name: Имя профиля
        account_name: Имя аккаунта

    Returns:
        bool: True если аккаунт является главным админом
    """
    try:
        admins_folder = get_profile_admins_folder(profile_name)
        session_file = admins_folder / f"{account_name}.session"
        return session_file.exists()

    except Exception as e:
        logger.error(f"❌ Ошибка проверки главного админа: {e}")
        return False


def load_bot_token(profile_name: str) -> str:
    """
    Загружает токен бота из файла профиля

    Args:
        profile_name: Имя профиля

    Returns:
        str: Токен бота или пустая строка если не найден
    """
    try:
        token_file = get_profile_bot_token_file(profile_name)

        if token_file.exists():
            token = token_file.read_text(encoding='utf-8').strip()
            logger.debug(f"📖 Токен бота загружен для профиля: {profile_name}")
            return token

        logger.debug(f"📄 Токен бота не найден для профиля: {profile_name}")
        return ""

    except Exception as e:
        logger.error(f"❌ Ошибка загрузки токена для {profile_name}: {e}")
        return ""


def save_bot_token(profile_name: str, token: str) -> bool:
    """
    Сохраняет токен бота в файл профиля

    Args:
        profile_name: Имя профиля
        token: Токен бота

    Returns:
        bool: True если сохранение успешно
    """
    try:
        # Обеспечиваем структуру профиля
        ensure_profile_structure(profile_name)

        token_file = get_profile_bot_token_file(profile_name)
        token_file.write_text(token.strip(), encoding='utf-8')

        logger.info(f"💾 Токен бота сохранен для профиля: {profile_name}")
        return True

    except Exception as e:
        logger.error(f"❌ Ошибка сохранения токена для {profile_name}: {e}")
        return False


def move_account_to_main_admins(profile_name: str, account_name: str,
                                session_file: Path, json_file: Path) -> bool:
    """
    НОВАЯ ФУНКЦИЯ: Перемещает аккаунт в папку главных админов профиля

    Args:
        profile_name: Имя профиля
        account_name: Имя аккаунта
        session_file: Путь к session файлу
        json_file: Путь к JSON файлу

    Returns:
        bool: True если перемещение успешно
    """
    try:
        # Получаем папку админов
        admins_folder = get_profile_admins_folder(profile_name)

        # Целевые пути
        session_dst = admins_folder / f"{account_name}.session"
        json_dst = admins_folder / f"{account_name}.json"

        # Проверяем что исходные файлы существуют
        if not session_file.exists() or not json_file.exists():
            logger.error(f"❌ Исходные файлы аккаунта {account_name} не найдены")
            return False

        # Перемещаем файлы
        import shutil
        shutil.move(str(session_file), str(session_dst))
        shutil.move(str(json_file), str(json_dst))

        logger.info(f"👑 Аккаунт {account_name} перемещен в главные админы профиля {profile_name}")
        return True

    except Exception as e:
        logger.error(f"❌ Ошибка перемещения {account_name} в админы профиля {profile_name}: {e}")
        return False


def move_main_admin_to_traffic(profile_name: str, account_name: str) -> bool:
    """
    НОВАЯ ФУНКЦИЯ: Возвращает главного админа обратно в трафик

    Args:
        profile_name: Имя профиля
        account_name: Имя аккаунта

    Returns:
        bool: True если перемещение успешно
    """
    try:
        # Получаем пути
        admins_folder = get_profile_admins_folder(profile_name)
        session_src = admins_folder / f"{account_name}.session"
        json_src = admins_folder / f"{account_name}.json"

        # Проверяем что файлы существуют
        if not session_src.exists() or not json_src.exists():
            logger.error(f"❌ Файлы главного админа {account_name} не найдены")
            return False

        # Целевые пути в трафике
        session_dst = WORK_ACCOUNTS_TRAFFER_FOLDER / f"{account_name}.session"
        json_dst = WORK_ACCOUNTS_TRAFFER_FOLDER / f"{account_name}.json"

        # Перемещаем файлы
        import shutil
        shutil.move(str(session_src), str(session_dst))
        shutil.move(str(json_src), str(json_dst))

        logger.info(f"🔄 Главный админ {account_name} возвращен в трафик из профиля {profile_name}")
        return True

    except Exception as e:
        logger.error(f"❌ Ошибка возврата админа {account_name} в трафик: {e}")
        return False


# Утилиты для отчетности и статистики
def get_profile_statistics(profile_name: str) -> Dict[str, any]:
    """
    НОВАЯ ФУНКЦИЯ: Получает статистику профиля

    Args:
        profile_name: Имя профиля

    Returns:
        Dict: Статистика профиля
    """
    try:
        profile_folder = get_profile_folder(profile_name)

        if not profile_folder.exists():
            return {"error": "Профиль не найден"}

        stats = {
            "profile_name": profile_name,
            "main_admins_count": 0,
            "has_bot_token": False,
            "users_count": 0,
            "chats_count": 0,
            "reports_count": 0
        }

        # Считаем главных админов
        admins_folder = get_profile_admins_folder(profile_name)
        admin_sessions = list(admins_folder.glob("*.session"))
        stats["main_admins_count"] = len(admin_sessions)

        # Проверяем токен бота
        token_file = get_profile_bot_token_file(profile_name)
        stats["has_bot_token"] = token_file.exists() and token_file.stat().st_size > 0

        # Считаем пользователей
        users_file = profile_folder / "База юзеров.txt"
        if users_file.exists():
            users_content = users_file.read_text(encoding='utf-8')
            users_lines = [line.strip() for line in users_content.split('\n') if line.strip()]
            stats["users_count"] = len(users_lines)

        # Считаем чаты
        chats_file = profile_folder / "База чатов.txt"
        if chats_file.exists():
            chats_content = chats_file.read_text(encoding='utf-8')
            chats_lines = [line.strip() for line in chats_content.split('\n') if line.strip()]
            stats["chats_count"] = len(chats_lines)

        # Считаем отчеты
        reports_folder = get_profile_reports_folder(profile_name)
        if reports_folder.exists():
            report_files = list(reports_folder.glob("*.txt")) + list(reports_folder.glob("*.json"))
            stats["reports_count"] = len(report_files)

        return stats

    except Exception as e:
        logger.error(f"❌ Ошибка получения статистики профиля {profile_name}: {e}")
        return {"error": str(e)}