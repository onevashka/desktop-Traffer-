# src/modules/impl/inviter/bot_manager.py
"""
Менеджер бота для управления админ-правами через aiogram
Отвечает за подключение к боту и управление правами администраторов
"""

import asyncio
from typing import Optional
from loguru import logger

from aiogram import Bot
from aiogram.types import ChatMemberAdministrator, ChatMemberOwner
from aiogram.exceptions import TelegramAPIError


class BotManager:
    """Менеджер бота для управления админ-правами"""

    def __init__(self, bot_token: str, proxy_url: str = None):
        self.bot_token = bot_token
        self.proxy_url = proxy_url
        self.bot: Optional[Bot] = None
        self.connected = False
        self.bot_username = None

    async def connect(self) -> bool:
        """Подключаемся к боту и проверяем его работоспособность"""
        try:
            logger.info("🤖 Подключение к боту...")

            # Создаем экземпляр бота
            if self.proxy_url:
                self.bot = Bot(token=self.bot_token, proxy=self.proxy_url)
            else:
                self.bot = Bot(token=self.bot_token)

            # Проверяем подключение
            me = await self.bot.get_me()
            self.bot_username = me.username
            self.connected = True

            logger.info(f"✅ Бот подключен: @{self.bot_username} (ID: {me.id})")
            return True

        except Exception as e:
            logger.error(f"❌ Ошибка подключения к боту: {e}")
            self.connected = False
            return False

    async def disconnect(self):
        """Отключаемся от бота"""
        try:
            if self.bot and self.connected:
                await self.bot.session.close()
                self.connected = False
                logger.info("🤖 Бот отключен")
        except Exception as e:
            logger.error(f"❌ Ошибка отключения бота: {e}")

    async def check_bot_admin_status(self, chat_link: str) -> bool:
        """Проверяет, является ли бот администратором в указанном чате"""
        try:
            # Получаем информацию о чате
            chat = await self.bot.get_chat(chat_link)
            chat_id = chat.id

            # Получаем информацию о боте в чате
            me = await self.bot.get_me()
            member = await self.bot.get_chat_member(chat_id=chat_id, user_id=me.id)

            # Проверяем статус
            is_admin = isinstance(member, (ChatMemberAdministrator, ChatMemberOwner))

            if is_admin:
                logger.info(f"✅ Бот @{self.bot_username} является админом в {chat_link}")
            else:
                logger.warning(f"⚠️ Бот @{self.bot_username} НЕ является админом в {chat_link}")

            return is_admin

        except Exception as e:
            logger.error(f"❌ Ошибка проверки статуса бота в {chat_link}: {e}")
            return False

    async def grant_admin_rights(self, chat_link: str, user_id: int, max_retries: int = 3) -> bool:
        """
        Выдает полные админ права пользователю

        Args:
            chat_link: Ссылка на чат
            user_id: ID пользователя
            max_retries: Количество попыток

        Returns:
            bool: True если права выданы успешно
        """
        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"🔑 Попытка {attempt}: выдача прав админа пользователю {user_id} в {chat_link}")

                # Получаем chat_id
                chat = await self.bot.get_chat(chat_link)
                chat_id = chat.id

                # Выдаем полные права админа
                await self.bot.promote_chat_member(
                    chat_id=chat_id,
                    user_id=user_id,
                    can_change_info=True,
                    can_delete_messages=True,
                    can_invite_users=True,
                    can_pin_messages=True,
                    can_promote_members=True,
                    can_manage_video_chats=True,
                    can_restrict_members=True,
                    can_post_messages=True,
                    can_edit_messages=True,
                )

                logger.info(f"✅ Права админа выданы пользователю {user_id} в {chat_link}")
                return True

            except TelegramAPIError as e:
                error_msg = str(e).lower()

                # Обрабатываем специфичные ошибки
                if 'chat not found' in error_msg and attempt < max_retries:
                    logger.warning(f"⚠️ Чат не найден, повтор через 1 сек...")
                    await asyncio.sleep(1)
                    continue
                elif 'user not found' in error_msg:
                    logger.error(f"❌ Пользователь {user_id} не найден")
                    break
                elif 'chat_admin_required' in error_msg:
                    logger.error(f"❌ Бот не имеет прав администратора в {chat_link}")
                    break
                elif 'user_already_admin' in error_msg:
                    logger.info(f"ℹ️ Пользователь {user_id} уже является админом")
                    return True
                else:
                    logger.error(f"❌ Ошибка выдачи прав (попытка {attempt}): {e}")
                    if attempt < max_retries:
                        await asyncio.sleep(2)
                        continue

            except Exception as e:
                logger.error(f"❌ Неожиданная ошибка при выдаче прав (попытка {attempt}): {e}")
                if attempt < max_retries:
                    await asyncio.sleep(2)
                    continue

        logger.error(f"❌ Не удалось выдать права админа пользователю {user_id} после {max_retries} попыток")
        return False

    async def revoke_admin_rights(self, chat_link: str, user_id: int, max_retries: int = 3) -> bool:
        """
        Забирает админ права у пользователя

        Args:
            chat_link: Ссылка на чат
            user_id: ID пользователя
            max_retries: Количество попыток

        Returns:
            bool: True если права забраны успешно
        """
        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"🔒 Попытка {attempt}: отзыв прав админа у пользователя {user_id} в {chat_link}")

                # Получаем chat_id
                chat = await self.bot.get_chat(chat_link)
                chat_id = chat.id

                # Забираем все права (устанавливаем в False)
                await self.bot.promote_chat_member(
                    chat_id=chat_id,
                    user_id=user_id,
                    can_change_info=False,
                    can_delete_messages=False,
                    can_invite_users=False,
                    can_pin_messages=False,
                    can_promote_members=False,
                    can_manage_video_chats=False,
                    can_restrict_members=False,
                    can_post_messages=False,
                    can_edit_messages=False,
                )

                logger.info(f"✅ Права админа отозваны у пользователя {user_id} в {chat_link}")
                return True

            except TelegramAPIError as e:
                error_msg = str(e).lower()

                # Обрабатываем специфичные ошибки
                if 'chat not found' in error_msg and attempt < max_retries:
                    logger.warning(f"⚠️ Чат не найден, повтор через 1 сек...")
                    await asyncio.sleep(1)
                    continue
                elif 'user not found' in error_msg:
                    logger.warning(f"⚠️ Пользователь {user_id} не найден (возможно уже покинул чат)")
                    return True  # Считаем успешным, так как цель достигнута
                elif 'chat_admin_required' in error_msg:
                    logger.error(f"❌ Бот не имеет прав администратора в {chat_link}")
                    break
                elif 'user_not_admin' in error_msg:
                    logger.info(f"ℹ️ Пользователь {user_id} уже не является админом")
                    return True
                else:
                    logger.error(f"❌ Ошибка отзыва прав (попытка {attempt}): {e}")
                    if attempt < max_retries:
                        await asyncio.sleep(2)
                        continue

            except Exception as e:
                logger.error(f"❌ Неожиданная ошибка при отзыве прав (попытка {attempt}): {e}")
                if attempt < max_retries:
                    await asyncio.sleep(2)
                    continue

        logger.error(f"❌ Не удалось отозвать права админа у пользователя {user_id} после {max_retries} попыток")
        return False

    async def get_chat_info(self, chat_link: str) -> Optional[dict]:
        """Получает информацию о чате"""
        try:
            chat = await self.bot.get_chat(chat_link)
            return {
                'id': chat.id,
                'title': chat.title,
                'username': chat.username,
                'type': chat.type,
                'members_count': getattr(chat, 'members_count', None)
            }
        except Exception as e:
            logger.error(f"❌ Ошибка получения информации о чате {chat_link}: {e}")
            return None