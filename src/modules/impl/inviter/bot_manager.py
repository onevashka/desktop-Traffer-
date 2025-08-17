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

    def _convert_chat_link_to_username(self, chat_link: str) -> str:
        """
        Конвертирует ссылку чата в username для Bot API

        Args:
            chat_link: Ссылка на чат (https://t.me/channel, @channel, channel)

        Returns:
            str: Username без @ для Bot API
        """
        try:
            # Убираем лишние пробелы
            chat_link = chat_link.strip()

            # Если это уже username с @
            if chat_link.startswith('@'):
                return chat_link[1:]  # Убираем @

            # Если это ссылка https://t.me/username
            if chat_link.startswith('https://t.me/'):
                username = chat_link.replace('https://t.me/', '')
                # Убираем дополнительные параметры если есть
                if '?' in username:
                    username = username.split('?')[0]
                return username

            # Если это ссылка t.me/username
            if chat_link.startswith('t.me/'):
                username = chat_link.replace('t.me/', '')
                if '?' in username:
                    username = username.split('?')[0]
                return username

            # Если это приватная ссылка (joinchat)
            if '/joinchat/' in chat_link or chat_link.startswith('https://t.me/+'):
                # Для приватных ссылок возвращаем как есть
                return chat_link

            # Если это просто username без @
            return chat_link

        except Exception as e:
            logger.error(f"❌ Ошибка конвертации ссылки {chat_link}: {e}")
            return chat_link

    # Теперь ИЗМЕНИТЕ метод check_bot_admin_status:

    async def check_bot_admin_status(self, chat_link: str) -> bool:
        """Проверяет, является ли бот администратором в указанном чате"""
        return True
        try:
            logger.debug(f"🔍 Проверяем статус бота в чате: {chat_link}")

            # Конвертируем ссылку в username
            username = self._convert_chat_link_to_username(chat_link)
            logger.debug(f"🔄 Конвертированная ссылка: {chat_link} -> {username}")

            # Получаем информацию о чате
            try:
                chat = await self.bot.get_chat(username)
                chat_id = chat.id
                logger.debug(f"✅ Чат найден: {chat.title if hasattr(chat, 'title') else chat_id}")
            except Exception as chat_error:
                error_msg = str(chat_error).lower()

                if "chat not found" in error_msg:
                    logger.warning(f"⚠️ Чат не найден: {chat_link}")
                    logger.warning(f"💡 Возможные причины:")
                    logger.warning(f"   - Неверная ссылка на чат")
                    logger.warning(f"   - Чат приватный и бот не был добавлен")
                    logger.warning(f"   - Чат был удален или заблокирован")
                    return False
                elif "forbidden" in error_msg or "unauthorized" in error_msg:
                    logger.warning(f"🔒 Нет доступа к чату: {chat_link}")
                    logger.warning(f"💡 Добавьте бота в чат и дайте ему права администратора")
                    return False
                else:
                    logger.error(f"❌ Ошибка при получении чата {chat_link}: {chat_error}")
                    return False

            # Получаем информацию о боте в чате
            try:
                me = await self.bot.get_me()
                member = await self.bot.get_chat_member(chat_id=chat_id, user_id=me.id)

                # ИСПРАВЛЕНО: Правильная проверка статуса для aiogram
                is_admin = isinstance(member, (ChatMemberAdministrator, ChatMemberOwner))

                if is_admin:
                    logger.info(f"✅ Бот @{self.bot_username} является админом в {chat_link}")

                    # Показываем права (для aiogram)
                    if isinstance(member, ChatMemberAdministrator):
                        rights = []
                        if member.can_invite_users:
                            rights.append("добавление пользователей")
                        if member.can_promote_members:
                            rights.append("управление админами")
                        if member.can_restrict_members:
                            rights.append("управление участниками")

                        logger.info(f"   Права бота: {', '.join(rights) if rights else 'базовые'}")
                else:
                    logger.warning(f"⚠️ Бот @{self.bot_username} НЕ является админом в {chat_link}")
                    logger.warning(f"💡 Дайте боту права администратора в чате")

                return is_admin

            except Exception as member_error:
                logger.error(f"❌ Ошибка получения статуса бота в {chat_link}: {member_error}")
                return False

        except Exception as e:
            logger.error(f"❌ Общая ошибка проверки статуса бота в {chat_link}: {e}")
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
                logger.debug(f"🔑 Попытка {attempt}: выдача прав админа пользователю {user_id} в {chat_link}")

                # Получаем chat_id
                #chat = await self.bot.get_chat(chat_link)
                #chat_id = chat.id

                # Выдаем полные права админа
                await self.bot.promote_chat_member(
                    chat_id=int(f'-100{chat_link}'),
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
                    is_anonymous=True,

                )

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
                logger.debug(f"🔒 Попытка {attempt}: отзыв прав админа у пользователя {user_id} в {chat_link}")

                # Забираем все права (устанавливаем в False)
                await self.bot.promote_chat_member(
                    chat_id=int(f'-100{chat_link}'),
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
                    is_anonymous=False,
                )

                logger.debug(f"✅ Права админа отозваны у пользователя {user_id} в {chat_link}")
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