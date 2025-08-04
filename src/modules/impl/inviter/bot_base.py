# backend/bot/bot_base.py

import asyncio
from aiogram.types import ChatMemberAdministrator, ChatMemberOwner
from aiogram import Bot
from loguru import logger


class BotBase:
    """
    ТОЛЬКО aiogram для управления ботом.
    БОТ НЕ ИНВАЙТИТ! Только управляет админ-правами!
    """

    def __init__(
            self,
            bot_username: str,
            bot_token: str,
            proxy_config=None
    ):
        self.bot_username = bot_username
        self.bot_token = bot_token
        self.logger = logger

        # ТОЛЬКО aiogram Bot API client
        proxy_url = None
        if proxy_config:
            proxy_url = self._build_proxy_url(proxy_config)

        if proxy_url:
            self.api = Bot(token=self.bot_token, proxy=proxy_url)
        else:
            self.api = Bot(token=self.bot_token)

    def _build_proxy_url(self, proxy_config):
        """Строит URL прокси для aiogram"""
        if not proxy_config:
            return None

        auth = ""
        if proxy_config.get('username'):
            auth = f"{proxy_config['username']}:{proxy_config['password']}@"

        proxy_type = proxy_config.get('proxy_type', 'socks5')
        return f"{proxy_type}://{auth}{proxy_config['addr']}:{proxy_config['port']}"

    async def connect(self):
        """Тестовое подключение бота"""
        try:
            # Простая проверка - получаем информацию о боте
            me = await self.api.get_me()
            logger.info(f"✅ Бот подключен: {me.first_name} (@{me.username})")
            return True

        except Exception as e:
            logger.error(f"❌ Ошибка подключения бота @{self.bot_username}: {e}")
            return False

    async def disconnect(self):
        """Отключение бота"""
        try:
            await self.api.session.close()
            logger.info(f"🔌 Бот @{self.bot_username} отключен")
        except Exception as e:
            logger.error(f"❌ Ошибка отключения бота: {e}")

    async def grant_admin(
            self,
            acc,  # Объект Account - используем его Telethon клиент для получения данных
            link: str,
            can_change_info: bool = True,
            can_delete_messages: bool = False,
            can_invite_users: bool = True,
            can_pin_messages: bool = True,
            can_promote_members: bool = False,
            can_manage_video_chats: bool = True,
            can_restrict_members: bool = False,
            can_post_messages: bool = True,
            can_edit_messages: bool = False,
            rank: str = ""
    ) -> bool:
        """
        Выдает права админа аккаунту в чате.
        Используем Telethon аккаунта для получения данных, aiogram для управления.
        """
        max_retries = 3
        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"🔧 Попытка {attempt}: выдача прав админа {acc.name} в {link}")

                # Получаем ID чата через Telethon аккаунта
                chat_entity = await acc.client.get_input_entity(link)
                chat = await acc.client.get_entity(chat_entity)
                chat_id = getattr(chat, 'id', None)
                if not chat_id:
                    raise ValueError(f"Не удалось получить chat_id для {link!r}")

                # Получаем user_id аккаунта через Telethon
                user_entity = await acc.client.get_entity('me')
                user_id = user_entity.id

                # Выдаем права через aiogram Bot API
                await self.api.promote_chat_member(
                    chat_id=int(f'-100{chat_id}'),
                    user_id=user_id,
                    can_change_info=can_change_info,
                    can_delete_messages=can_delete_messages,
                    can_invite_users=can_invite_users,
                    can_pin_messages=can_pin_messages,
                    can_promote_members=can_promote_members,
                    can_manage_video_chats=can_manage_video_chats,
                    can_restrict_members=can_restrict_members,
                    can_post_messages=can_post_messages,
                    can_edit_messages=can_edit_messages,
                )

                logger.info(f"✅ Права админа выданы {acc.name} в {link}")
                return True

            except Exception as e:
                msg = str(e).lower()
                logger.error(f"❌ Ошибка выдачи прав (попытка {attempt}): {e}")

                # Если чат не найден — ждем и повторяем
                if 'chat not found' in msg and attempt < max_retries:
                    logger.info(f"⏳ Чат не найден, ждем 1с и повторяем...")
                    await asyncio.sleep(1)
                    continue

                # Иначе пробрасываем дальше
                if attempt == max_retries:
                    raise

        return False

    async def revoke_admin(
            self,
            acc,  # Объект Account - используем его Telethon клиент для получения данных
            link: str
    ) -> bool:
        """
        Снимает у указанного аккаунта все админские права в чате.
        Используем Telethon аккаунта для получения данных, aiogram для управления.
        """
        try:
            logger.info(f"🔄 Отзыв прав админа у {acc.name} в {link}")

            # Получаем ID чата через Telethon аккаунта
            chat_entity = await acc.client.get_input_entity(link)
            chat = await acc.client.get_entity(chat_entity)
            chat_id = getattr(chat, 'id', None)
            if not chat_id:
                raise ValueError(f"Не удалось получить chat_id для {link!r}")

            # Получаем user_id аккаунта через Telethon
            user = await acc.client.get_entity('me')
            user_id = user.id

            # Отзываем права через aiogram Bot API (все флаги в False)
            await self.api.promote_chat_member(
                chat_id=int(f'-100{chat_id}'),
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

            logger.info(f"✅ Права админа отозваны у {acc.name} в {link}")
            return True

        except Exception as e:
            # Если у бота нет прав менять админов — просто логируем
            if "CHAT_ADMIN_REQUIRED" in str(e):
                logger.warning(f"⚠️ У бота нет прав для отзыва админки: {e}")
                return False

            logger.error(f"❌ Ошибка отзыва прав у {acc.name}: {e}")
            return False

    async def has_self_admin(self, link: str) -> bool:
        """
        Проверяет, состоит ли этот бот в списке админов указанного чата.
        ТОЛЬКО aiogram, без Telethon.
        """
        try:
            # Получаем информацию о чате через aiogram
            chat = await self.api.get_chat(link)
            chat_id = chat.id

            # Узнаём свой user_id
            me = await self.api.get_me()
            my_id = me.id

            # Запрашиваем сведения о себе в этом чате
            member = await self.api.get_chat_member(chat_id=chat_id, user_id=my_id)

            # Проверяем, админ ли мы (или владелец)
            is_admin = isinstance(member, (ChatMemberAdministrator, ChatMemberOwner))

            if is_admin:
                logger.info(f"✅ Бот @{self.bot_username} является админом в {link}")
            else:
                logger.warning(f"⚠️ Бот @{self.bot_username} НЕ является админом в {link}")

            return is_admin

        except Exception as e:
            logger.warning(f"⚠️ Не удалось проверить админство бота @{self.bot_username} в {link}: {e}")
            return False