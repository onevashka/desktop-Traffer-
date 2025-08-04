# src/modules/impl/inviter/bot_creator.py
"""
Создание ботов через BotFather
"""

import re
import asyncio
import random
from typing import Optional, Dict
from loguru import logger

from .bot_utils import (
    extract_token_from_text,
    normalize_username,
    generate_unique_username,
    create_bot_name,
    validate_bot_token
)


class BotCreator:
    """Класс для создания ботов через @BotFather"""

    async def create_bot_via_botfather(
            self,
            account,
            profile_name: str,
            timeout: int = 120
    ) -> Optional[Dict[str, str]]:
        """
        Создает бота через @BotFather

        Args:
            account: Аккаунт для создания бота
            profile_name: Название профиля для генерации имени
            timeout: Таймаут операции

        Returns:
            Словарь с token и username или None при ошибке
        """
        try:
            logger.info(f"🤖 Создание бота через @BotFather для {account.name}")

            if not account.client.is_connected():
                await account.client.connect()

            # Генерируем данные для бота
            bot_name = self._generate_bot_name(profile_name, account.phone)
            base_username = self._generate_base_username(profile_name, account.phone)

            logger.info(f"   📝 Имя бота: {bot_name}")
            logger.info(f"   📝 Базовый username: {base_username}")

            # Начинаем диалог с BotFather
            async with account.client.conversation('@BotFather', timeout=timeout) as conv:
                # 1. Отправляем команду /newbot
                await conv.send_message('/newbot')
                await asyncio.sleep(1)

                response = await conv.get_response()
                logger.debug(f"BotFather ответ на /newbot: {response.text[:100]}...")

                # 2. Отправляем имя бота
                await conv.send_message(bot_name)
                await asyncio.sleep(1)

                response = await conv.get_response()
                logger.debug(f"BotFather ответ на имя: {response.text[:100]}...")

                # 3. Отправляем username бота (с повторными попытками)
                username = await self._negotiate_username(conv, base_username, account.phone, timeout)

                if not username:
                    logger.error("❌ Не удалось согласовать username бота")
                    return None

                # 4. Получаем финальный ответ с токеном
                response = await conv.get_response()
                token = extract_token_from_text(response.text)

                if not token:
                    logger.error(f"❌ Не удалось извлечь токен из ответа: {response.text}")
                    return None

                if not validate_bot_token(token):
                    logger.error(f"❌ Невалидный токен: {token}")
                    return None

                logger.info(f"✅ Бот создан успешно!")
                logger.info(f"   🤖 Username: @{username}")
                logger.info(f"   🔑 Token: {token[:15]}...")

                return {
                    'token': token,
                    'username': username,
                    'name': bot_name
                }

        except asyncio.TimeoutError:
            logger.error(f"⏰ Таймаут создания бота ({timeout}s)")
            return None
        except Exception as e:
            logger.error(f"❌ Ошибка создания бота: {e}")
            return None

    async def _negotiate_username(
            self,
            conv,
            base_username: str,
            phone: str,
            timeout: int
    ) -> Optional[str]:
        """
        Согласовывает username бота с BotFather

        Args:
            conv: Объект conversation
            base_username: Базовый username
            phone: Номер телефона для уникальности
            timeout: Общий таймаут

        Returns:
            Финальный username или None
        """
        start_time = asyncio.get_event_loop().time()
        max_attempts = 10
        attempt = 0

        # Начинаем с базового username
        current_username = normalize_username(base_username)
        if not current_username.lower().endswith('bot'):
            current_username += 'bot'
        current_username = current_username[:32]

        while attempt < max_attempts:
            # Проверяем таймаут
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > timeout - 10:  # Оставляем 10 секунд запаса
                logger.error(f"⏰ Таймаут согласования username")
                return None

            attempt += 1
            logger.debug(f"🔄 Попытка #{attempt}: предлагаем username @{current_username}")

            # Отправляем username
            await conv.send_message(current_username)
            await asyncio.sleep(2)  # Даем время BotFather обработать

            # Получаем ответ
            response = await conv.get_response()
            text = response.text.strip()
            text_lower = text.lower()

            logger.debug(f"BotFather ответ: {text[:100]}...")

            # Проверяем содержит ли ответ токен (успех!)
            if 'token' in text_lower and ':' in text:
                logger.info(f"✅ Username согласован: @{current_username}")
                return current_username

            # Анализируем ошибки и генерируем новый username
            if 'already taken' in text_lower or 'уже занято' in text_lower:
                logger.debug("❌ Username занят, генерируем новый")
                current_username = generate_unique_username(base_username, phone)

            elif 'must end in' in text_lower or 'должен заканчиваться' in text_lower:
                logger.debug("❌ Username должен заканчиваться на 'bot'")
                if not current_username.lower().endswith('bot'):
                    current_username = current_username.rstrip('Bb').rstrip('oO').rstrip('tT') + 'bot'
                else:
                    # Если уже заканчивается на bot, генерируем новый
                    current_username = generate_unique_username(base_username, phone)

            elif 'invalid' in text_lower or 'недопустим' in text_lower:
                logger.debug("❌ Username недопустим, генерируем новый")
                current_username = generate_unique_username(base_username, phone)

            elif 'too long' in text_lower or 'слишком длинн' in text_lower:
                logger.debug("❌ Username слишком длинный, сокращаем")
                current_username = current_username[:28] + 'bot'

            elif 'too short' in text_lower or 'слишком короток' in text_lower:
                logger.debug("❌ Username слишком короткий, удлиняем")
                current_username = current_username[:-3] + '_bot'

            else:
                logger.warning(f"⚠️ Неизвестная ошибка от BotFather: {text[:100]}")
                current_username = generate_unique_username(base_username, phone)

            # Обрезаем до максимальной длины
            current_username = current_username[:32]

            await asyncio.sleep(1)  # Небольшая пауза между попытками

        logger.error(f"❌ Не удалось согласовать username после {max_attempts} попыток")
        return None

    def _generate_bot_name(self, profile_name: str, phone: str) -> str:
        """Генерирует красивое имя для бота"""
        # Используем название профиля если оно осмысленное
        if profile_name and len(profile_name) > 3 and profile_name != "Профиль":
            base_name = f"{profile_name} Inviter Bot"
        else:
            base_name = "Invite Bot"

        # Добавляем последние цифры телефона для уникальности
        if phone:
            phone_digits = re.sub(r'\D', '', phone)
            if len(phone_digits) >= 4:
                base_name += f" {phone_digits[-4:]}"

        # Ограничиваем длину (максимум 64 символа для имени бота)
        if len(base_name) > 60:
            base_name = base_name[:60] + "..."

        return base_name

    def _generate_base_username(self, profile_name: str, phone: str) -> str:
        """Генерирует базовый username для бота"""
        # Используем название профиля если оно подходит
        if profile_name and len(profile_name) > 2:
            # Очищаем название профиля для username
            clean_profile = re.sub(r'[^a-zA-Z0-9_]', '', profile_name.lower())
            if clean_profile and len(clean_profile) >= 3:
                base = f"{clean_profile}_inviter"
            else:
                base = "inviter"
        else:
            base = "inviter"

        # Добавляем цифры телефона для уникальности
        if phone:
            phone_digits = re.sub(r'\D', '', phone)
            if len(phone_digits) >= 4:
                base += f"_{phone_digits[-4:]}"

        # Нормализуем
        base = normalize_username(base)

        # Ограничиваем длину (оставляем место для 'bot')
        base = base[:28]

        return base

    async def delete_bot(self, account, bot_username: str) -> bool:
        """
        Удаляет бота через @BotFather (опциональная функция)

        Args:
            account: Аккаунт владелец бота
            bot_username: Username бота для удаления

        Returns:
            True если бот удален успешно
        """
        try:
            logger.info(f"🗑️ Удаление бота @{bot_username}")

            if not account.client.is_connected():
                await account.client.connect()

            async with account.client.conversation('@BotFather', timeout=60) as conv:
                # Отправляем команду /deletebot
                await conv.send_message('/deletebot')
                await asyncio.sleep(1)

                response = await conv.get_response()

                # Если у нас несколько ботов, BotFather может показать список
                if 'choose a bot' in response.text.lower():
                    # Отправляем username бота
                    await conv.send_message(f'@{bot_username}')
                    await asyncio.sleep(1)
                    response = await conv.get_response()

                # Подтверждаем удаление
                if 'yes' in response.text.lower() or 'да' in response.text.lower():
                    await conv.send_message('Yes, I am totally sure.')
                    await asyncio.sleep(1)
                    response = await conv.get_response()

                    if 'done' in response.text.lower() or 'готово' in response.text.lower():
                        logger.info(f"✅ Бот @{bot_username} удален")
                        return True

                logger.warning(f"⚠️ Не удалось удалить бота: {response.text}")
                return False

        except Exception as e:
            logger.error(f"❌ Ошибка удаления бота: {e}")
            return False

    async def get_bot_info(self, account) -> Optional[Dict]:
        """
        Получает информацию о ботах пользователя

        Args:
            account: Аккаунт для запроса

        Returns:
            Словарь с информацией о ботах
        """
        try:
            logger.info(f"ℹ️ Получение информации о ботах для {account.name}")

            if not account.client.is_connected():
                await account.client.connect()

            async with account.client.conversation('@BotFather', timeout=30) as conv:
                # Отправляем команду /mybots
                await conv.send_message('/mybots')
                await asyncio.sleep(2)

                response = await conv.get_response()

                # Парсим ответ (базовая реализация)
                bots_info = {
                    'raw_response': response.text,
                    'has_bots': 'choose a bot' in response.text.lower() or '@' in response.text
                }

                logger.info(f"ℹ️ Информация о ботах получена")
                return bots_info

        except Exception as e:
            logger.error(f"❌ Ошибка получения информации о ботах: {e}")
            return None

    def validate_bot_name(self, name: str) -> bool:
        """Валидирует имя бота"""
        if not name or len(name.strip()) < 1:
            return False

        if len(name) > 64:
            return False

        # Имя может содержать любые символы кроме некоторых служебных
        forbidden_chars = ['<', '>', '&', '"']
        for char in forbidden_chars:
            if char in name:
                return False

        return True

    def validate_bot_username(self, username: str) -> bool:
        """Валидирует username бота"""
        if not username:
            return False

        # Убираем @ если есть
        clean_username = username.lstrip('@')

        # Длина от 5 до 32 символов
        if len(clean_username) < 5 or len(clean_username) > 32:
            return False

        # Должен заканчиваться на 'bot'
        if not clean_username.lower().endswith('bot'):
            return False

        # Только латинские буквы, цифры и подчеркивания
        if not re.match(r'^[A-Za-z0-9_]+', clean_username):
            return False

        # Не может начинаться с цифры
        if clean_username[0].isdigit():
            return False

        return True

    def __str__(self):
        return "BotCreator"

    def __repr__(self):
        return self.__str__()