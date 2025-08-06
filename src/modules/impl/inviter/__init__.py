# src/modules/impl/inviter/__init__.py
"""
Модуль инвайтера - массовые инвайты в Telegram чаты
"""
from loguru import logger
from typing import List
import os

from .inviter_manager import (
    InviterModuleManager,
    get_inviter_module_manager,
    init_inviter_module,
    get_inviter_stats,
    get_all_profiles_for_gui,
    create_profile,
    delete_profile,
    start_profile,
    stop_profile,
    update_profile_users,
    update_profile_chats,
    update_profile_config,
    start_all_profiles,
    stop_all_profiles,
    refresh_inviter_module,
    get_profile_progress
)

from .profile_manager import InviterProfileManager

__all__ = [
    # Основные классы
    'InviterModuleManager',
    'InviterProfileManager',

    # Функции инициализации
    'get_inviter_module_manager',
    'init_inviter_module',

    # Функции для GUI - статистика
    'get_inviter_stats',

    # Функции для GUI - профили
    'get_all_profiles_for_gui',
    'create_profile',
    'delete_profile',

    # Функции для GUI - управление процессами
    'start_profile',
    'stop_profile',
    'start_all_profiles',
    'stop_all_profiles',

    # Функции для GUI - данные
    'update_profile_users',
    'update_profile_chats',
    'update_profile_config',

    # Функции обслуживания
    'refresh_inviter_module',

    # Функции прогресса
    'get_profile_progress',

    'get_profile_users_from_file',
    'get_profile_chats_from_file',
]


def get_profile_users_from_file(profile_name: str) -> List[str]:
    """Загружает актуальные данные пользователей напрямую из файла"""
    try:
        from src.modules.impl.inviter.profile_manager import InviterProfileManager
        from paths import WORK_INVITER_FOLDER
        import os

        profile_folder = WORK_INVITER_FOLDER / profile_name
        users_file_path = os.path.join(profile_folder, 'База юзеров.txt')

        if not os.path.exists(users_file_path):
            logger.warning(f"⚠️ Файл пользователей не существует: {users_file_path}")
            return []

        with open(users_file_path, 'r', encoding='utf-8') as f:
            users = []
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    if line.startswith('@'):
                        line = line[1:]
                    if line:
                        users.append(line)

        logger.info(f"📁 Загружено из файла {users_file_path}: {len(users)} пользователей")
        return users

    except Exception as e:
        logger.error(f"❌ Ошибка загрузки пользователей из файла {profile_name}: {e}")
        return None


def get_profile_chats_from_file(profile_name: str) -> List[str]:
    """Загружает актуальные данные чатов напрямую из файла"""
    try:
        from src.modules.impl.inviter.profile_manager import InviterProfileManager
        import os

        profile_manager = InviterProfileManager()
        profile = profile_manager.get_profile(profile_name)

        if not profile:
            logger.error(f"❌ Профиль {profile_name} не найден")
            return None

        profile_folder = profile['folder_path']
        chats_file_path = os.path.join(profile_folder, 'База чатов.txt')

        if not os.path.exists(chats_file_path):
            logger.warning(f"⚠️ Файл чатов не существует: {chats_file_path}")
            return []

        with open(chats_file_path, 'r', encoding='utf-8') as f:
            chats = []
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    chats.append(line)

        logger.info(f"📁 Загружено из файла {chats_file_path}: {len(chats)} чатов")
        return chats

    except Exception as e:
        logger.error(f"❌ Ошибка загрузки чатов из файла {profile_name}: {e}")
        return None