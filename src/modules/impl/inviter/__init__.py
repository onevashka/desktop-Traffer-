# src/modules/impl/inviter/__init__.py
"""
Модуль инвайтера - массовые инвайты в Telegram чаты
"""

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
    'get_profile_progress'
]