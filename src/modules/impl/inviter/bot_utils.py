# src/modules/impl/inviter/bot_utils.py
"""
Утилиты для работы с ботами в Telegram
"""

import re
import random
import string
from typing import Optional


def extract_token_from_text(text: str) -> Optional[str]:
    """
    Извлекает токен бота из текста сообщения BotFather

    Args:
        text: Текст сообщения

    Returns:
        Токен бота или None если не найден
    """
    # Паттерн для токена: число:строка с буквами и цифрами
    token_pattern = r'\d+:[A-Za-z0-9_-]{35}'
    match = re.search(token_pattern, text)

    if match:
        return match.group(0)
    return None


def normalize_username(username: str) -> str:
    """
    Нормализует username для бота

    Args:
        username: Исходный username

    Returns:
        Нормализованный username
    """
    # Убираем @ если есть
    clean = username.lstrip('@')

    # Удаляем все символы кроме латинских букв, цифр и подчеркиваний
    clean = re.sub(r'[^a-zA-Z0-9_]', '', clean)

    # Если начинается с цифры, добавляем букву впереди
    if clean and clean[0].isdigit():
        clean = 'b' + clean

    # Если пустая строка, возвращаем базовый username
    if not clean:
        return 'inviterbot'

    return clean


def generate_unique_username(base: str, phone: str = None) -> str:
    """
    Генерирует уникальный username для бота

    Args:
        base: Базовый username
        phone: Номер телефона для уникальности

    Returns:
        Уникальный username
    """
    # Нормализуем базу
    clean_base = normalize_username(base)

    # Генерируем случайную строку
    random_suffix = ''.join(random.choices(string.ascii_lowercase, k=4))

    # Добавляем цифры телефона если есть
    if phone:
        phone_digits = re.sub(r'\D', '', phone)
        if len(phone_digits) >= 4:
            random_suffix = phone_digits[-2:] + random_suffix[:2]

    # Собираем username
    if clean_base.lower().endswith('bot'):
        # Если уже заканчивается на bot, заменяем bot на случайную строку + bot
        username = clean_base[:-3] + '_' + random_suffix + 'bot'
    else:
        # Иначе просто добавляем случайную строку + bot
        username = clean_base + '_' + random_suffix + 'bot'

    # Обрезаем до допустимой длины
    return username[:32]


def create_bot_name(profile_name: str) -> str:
    """
    Создает имя для бота

    Args:
        profile_name: Название профиля

    Returns:
        Имя бота
    """
    if not profile_name or len(profile_name) < 3:
        return f"Invite Bot {random.randint(1000, 9999)}"

    # Очищаем название профиля
    clean_name = re.sub(r'[^\w\s]', '', profile_name)

    # Если очистили слишком много, используем дефолтное имя
    if len(clean_name) < 3:
        return f"Invite Bot {random.randint(1000, 9999)}"

    # Создаем имя бота
    bot_name = f"{clean_name} Inviter Bot"

    # Если слишком длинное, обрезаем
    if len(bot_name) > 60:
        bot_name = bot_name[:57] + "..."

    return bot_name


def validate_bot_token(token: str) -> bool:
    """
    Проверяет валидность токена бота

    Args:
        token: Токен для проверки

    Returns:
        True если токен валидный
    """
    # Паттерн для токена: число:строка из букв и цифр длиной 35 символов
    return bool(re.match(r'^\d+:[A-Za-z0-9_-]{35}$', token))