# backend/bot/bot_creator.py

import re
import os
import json
import asyncio
import threading
from typing import Optional, Dict
from loguru import logger
from telethon import TelegramClient

_file_lock = threading.Lock()


def extract_token_from_text(text: str) -> str:
    """
    Парсит из текста BotFather токен вида 123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
    """
    m = re.search(r'(\d+:[A-Za-z0-9_-]+)', text)
    if not m:
        raise ValueError(f"Не удалось найти токен в тексте: {text!r}")
    return m.group(1)


def generate_username(base: str, phone: str) -> str:
    """
    Генерирует уникальный username на основе базового имени и номера телефона
    """
    # Берем последние 4 цифры телефона
    phone_suffix = ''.join(filter(str.isdigit, phone))[-4:]

    # Убираем 'bot' если есть в конце
    clean_base = base.lower()
    if clean_base.endswith('bot'):
        clean_base = clean_base[:-3]

    # Добавляем суффикс и 'bot'
    new_username = f"{clean_base}{phone_suffix}bot"

    # Ограничиваем длину
    return new_username[:32]


def normalize_username(username: str) -> str:
    """
    Нормализует username: убирает недопустимые символы, приводит к нижнему регистру
    """
    # Убираем все кроме букв, цифр и подчеркиваний
    normalized = re.sub(r'[^a-zA-Z0-9_]', '', username.lower())

    # Убираем начальные/конечные подчеркивания
    normalized = normalized.strip('_')

    # Если пустая строка, возвращаем дефолтное имя
    if not normalized:
        normalized = 'mybot'

    return normalized


async def get_bot_token_from_account(account) -> Optional[str]:
    """
    Получает токен бота из JSON файла аккаунта.
    Проверяет ключ 'bot_token' в account.account_data
    """
    try:
        account_data = account.account_data
        token = account_data.get('bot_token')

        if token:
            logger.info(f"[{account.name}] ✅ Найден токен существующего бота: {token[:10]}...")
            return token
        else:
            logger.info(f"[{account.name}] ℹ️ Токен бота не найден в JSON")
            return None

    except Exception as e:
        logger.error(f"[{account.name}] ❌ Ошибка получения токена из JSON: {e}")
        return None


async def save_bot_token_to_account(account, token: str, username: str) -> bool:
    """
    Сохраняет токен бота в JSON файл аккаунта.
    """
    try:
        with _file_lock:
            # Читаем текущие данные
            with open(account.json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Добавляем токен и username бота
            data['bot_token'] = token
            data['bot_username'] = username

            # Сохраняем обратно
            with open(account.json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            # Обновляем данные в объекте
            account.account_data['bot_token'] = token
            account.account_data['bot_username'] = username

        logger.info(f"[{account.name}] ✅ Токен бота сохранен в JSON: @{username}")
        return True

    except Exception as e:
        logger.error(f"[{account.name}] ❌ Ошибка сохранения токена в JSON: {e}")
        return False


async def create_bot_via_botfather(
        account,  # Объект Account
        name: str,
        username: str,
        botfather: str = 'BotFather',
        timeout: int = 120
) -> Optional[str]:
    """
    Создаёт нового бота через @BotFather и возвращает токен.
    КОПИЯ ТВОЕГО КОДА с небольшими адаптациями.
    """
    client: TelegramClient = account.client
    phone = account.account_data.get('phone', '')

    try:
        logger.info(f"[{account.name}] 🤖 Создание бота через @{botfather}")

        async with client.conversation(botfather, timeout=timeout) as conv:
            # 1) /newbot
            logger.info(f"[{account.name}] 📝 Отправляем /newbot")
            await conv.send_message('/newbot')

            # 2) ask for name
            resp = await conv.get_response()
            logger.info(f"[{account.name}] 📝 Отправляем имя: {name}")
            await conv.send_message(name)

            # 3) ask for username
            resp = await conv.get_response()

            # первоначальный clean username (с гарантией окончания bot)
            clean = normalize_username(username)
            if not clean.lower().endswith('bot'):
                clean += 'bot'
            clean = clean[:32]

            start = asyncio.get_event_loop().time()
            attempt = 0

            while True:
                attempt += 1
                elapsed = asyncio.get_event_loop().time() - start
                if elapsed > timeout:
                    logger.error(f"[{account.name}] ❌ Таймаут создания бота")
                    raise TimeoutError("Не дождались ответа от BotFather")

                logger.info(f"[{account.name}] 📝 Попытка {attempt}: username {clean}")
                await conv.send_message(clean)
                resp = await conv.get_response()
                text = resp.text.strip()
                lower = text.lower()

                # 4) если получили сообщение с токеном — выходим из цикла
                if 'token' in lower and ':' in text:
                    logger.info(f"[{account.name}] 🎉 Токен получен!")
                    break

                # иначе — ошибка username, генерируем новый
                if 'already taken' in lower:
                    logger.warning(f"[{account.name}] ⚠️ Username занят, генерируем новый")
                    clean = generate_username(clean, phone)
                elif 'must end in' in lower:
                    logger.warning(f"[{account.name}] ⚠️ Должен заканчиваться на bot")
                    core = normalize_username(clean)
                    clean = (core + 'bot')[:32]
                else:
                    logger.warning(f"[{account.name}] ⚠️ Другая ошибка, генерируем новый")
                    clean = generate_username(clean, phone)

                clean = clean[:32]

                # Защита от бесконечного цикла
                if attempt > 10:
                    logger.error(f"[{account.name}] ❌ Слишком много попыток")
                    return None

            # 5) Извлекаем токен
            token = extract_token_from_text(text)
            final_username = clean  # Сохраняем финальный username

            logger.info(f"[{account.name}] ✅ Бот создан: @{final_username}")
            logger.info(f"[{account.name}] 🔑 Токен: {token[:10]}...")

            # 6) Сохраняем токен в JSON аккаунта
            await save_bot_token_to_account(account, token, final_username)

            return token

    except Exception as e:
        logger.error(f"[{account.name}] ❌ Ошибка создания бота: {e}")
        return None


async def get_or_create_bot_for_account(account) -> Optional[Dict[str, str]]:
    """
    Главная функция: получает существующего бота или создает нового.

    1. Проверяет JSON аккаунта на наличие bot_token
    2. Если есть - возвращает данные
    3. Если нет - создает бота через BotFather

    Returns:
        {'token': str, 'username': str} или None
    """
    try:
        logger.info(f"[{account.name}] 🤖 Получение/создание бота...")

        # 1. Проверяем есть ли уже токен в JSON
        existing_token = await get_bot_token_from_account(account)
        if existing_token:
            username = account.account_data.get('bot_username', f"{account.name}_bot")
            logger.info(f"[{account.name}] ✅ Используем существующего бота: @{username}")
            return {
                'token': existing_token,
                'username': username
            }

        # 2. Токена нет, создаем нового бота
        logger.info(f"[{account.name}] 🔨 Создаем нового бота...")

        # Название бота = имя аккаунта + "_bot" как ты просил
        bot_name = f"Admin Inviter {account.name}"
        bot_username = f"{account.name}_bot"

        # Создаем бота через BotFather
        token = await create_bot_via_botfather(
            account=account,
            name=bot_name,
            username=bot_username
        )

        if token:
            # Получаем финальный username из JSON (может отличаться из-за конфликтов)
            final_username = account.account_data.get('bot_username', bot_username)

            logger.info(f"[{account.name}] 🎉 Бот создан и сохранен: @{final_username}")
            return {
                'token': token,
                'username': final_username
            }
        else:
            logger.error(f"[{account.name}] ❌ Не удалось создать бота")
            return None

    except Exception as e:
        logger.error(f"[{account.name}] ❌ Ошибка получения/создания бота: {e}")
        return None