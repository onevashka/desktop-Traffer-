# src/modules/impl/inviter/admin_rights_manager.py

import asyncio
from typing import Optional
from loguru import logger

from .bot_manager import BotManager


class AdminRightsManager:
    """
    Менеджер для управления админ-правами через бота.
    Интегрированный с существующей логикой инвайтера.
    """

    def __init__(self, bot_manager: BotManager, profile_name: str):
        self.bot_manager = bot_manager
        self.profile_name = profile_name

    async def grant_admin_rights(
            self,
            account,  # Объект Account из существующей системы
            chat_link: str,
            max_retries: int = 3,
            retry_delay: int = 2
    ) -> bool:
        """
        Выдает права админа аккаунту с повторными попытками
        """
        for attempt in range(1, max_retries + 1):
            try:
                logger.info(
                    f"[{self.profile_name}] 🔧 Попытка {attempt}/{max_retries}: выдача прав админа {account.name} в {chat_link}")

                # Проверяем, что бот инициализирован
                if not self.bot_manager.is_initialized:
                    logger.error(f"[{self.profile_name}] ❌ Бот-менеджер не инициализирован")
                    return False

                # Проверяем, что бот является админом в чате
                if not await self.bot_manager.check_admin_rights(chat_link):
                    logger.error(f"[{self.profile_name}] ❌ Бот не является админом в {chat_link}")
                    logger.info(
                        f"[{self.profile_name}] 💡 Убедитесь, что бот @{self.bot_manager.bot_username} добавлен в чат как админ")
                    return False

                # Убеждаемся, что аккаунт подключен
                if not account.client:
                    await account.create_client()

                if not await account.connect():
                    logger.error(f"[{self.profile_name}] ❌ Не удалось подключить аккаунт {account.name}")
                    return False

                # Выдаем права через бота
                result = await self.bot_manager.grant_admin_rights(account, chat_link)

                if result:
                    logger.info(f"[{self.profile_name}] ✅ Права админа успешно выданы: {account.name}")
                    return True
                else:
                    logger.warning(f"[{self.profile_name}] ⚠️ Не удалось выдать права админа: {account.name}")

                    if attempt < max_retries:
                        logger.info(f"[{self.profile_name}] ⏳ Ждем {retry_delay}с перед повтором...")
                        await asyncio.sleep(retry_delay)

            except Exception as e:
                logger.error(
                    f"[{self.profile_name}] ❌ Ошибка выдачи прав админа {account.name} (попытка {attempt}): {e}")

                if attempt < max_retries:
                    logger.info(f"[{self.profile_name}] ⏳ Ждем {retry_delay}с перед повтором...")
                    await asyncio.sleep(retry_delay)

        logger.error(
            f"[{self.profile_name}] ❌ Не удалось выдать права админа {account.name} после {max_retries} попыток")
        return False

    async def revoke_admin_rights(
            self,
            account,  # Объект Account из существующей системы
            chat_link: str,
            max_retries: int = 2,
            retry_delay: int = 1
    ) -> bool:
        """
        Отзывает права админа у аккаунта с повторными попытками
        """
        for attempt in range(1, max_retries + 1):
            try:
                logger.info(
                    f"[{self.profile_name}] 🔄 Попытка {attempt}/{max_retries}: отзыв прав админа {account.name} в {chat_link}")

                # Проверяем, что бот инициализирован
                if not self.bot_manager.is_initialized:
                    logger.warning(f"[{self.profile_name}] ⚠️ Бот-менеджер не инициализирован, пропускаем отзыв прав")
                    return True  # Считаем успешным, так как права и так не активны

                # Убеждаемся, что аккаунт подключен
                if not account.client:
                    await account.create_client()

                if not await account.connect():
                    logger.warning(
                        f"[{self.profile_name}] ⚠️ Не удалось подключить аккаунт {account.name} для отзыва прав")
                    return True  # Не критично для отзыва

                # Отзываем права через бота
                result = await self.bot_manager.revoke_admin_rights(account, chat_link)

                if result:
                    logger.info(f"[{self.profile_name}] ✅ Права админа успешно отозваны: {account.name}")
                    return True
                else:
                    logger.warning(f"[{self.profile_name}] ⚠️ Не удалось отозвать права админа: {account.name}")

                    if attempt < max_retries:
                        logger.info(f"[{self.profile_name}] ⏳ Ждем {retry_delay}с перед повтором...")
                        await asyncio.sleep(retry_delay)

            except Exception as e:
                logger.error(
                    f"[{self.profile_name}] ❌ Ошибка отзыва прав админа {account.name} (попытка {attempt}): {e}")

                if attempt < max_retries:
                    logger.info(f"[{self.profile_name}] ⏳ Ждем {retry_delay}с перед повтором...")
                    await asyncio.sleep(retry_delay)

        # Для отзыва прав не критично, если не получилось
        logger.warning(
            f"[{self.profile_name}] ⚠️ Не удалось отозвать права админа {account.name} после {max_retries} попыток")
        return False

    async def verify_admin_status(self, account, chat_link: str) -> bool:
        """
        Проверяет, является ли аккаунт админом в чате
        """
        try:
            if not account.client:
                await account.create_client()

            if not await account.connect():
                logger.warning(
                    f"[{self.profile_name}] ⚠️ Не удалось подключить аккаунт {account.name} для проверки статуса")
                return False

            # Получаем информацию о чате
            chat_entity = await account.client.get_input_entity(chat_link)
            chat = await account.client.get_entity(chat_entity)

            # Получаем информацию о себе
            me = await account.client.get_me()

            # Проверяем права в чате
            from telethon.tl.functions.channels import GetParticipantRequest
            try:
                participant = await account.client(GetParticipantRequest(
                    channel=chat,
                    participant=me.id
                ))

                # Проверяем тип участника
                from telethon.tl.types import ChannelParticipantAdmin, ChannelParticipantCreator
                is_admin = isinstance(participant.participant, (ChannelParticipantAdmin, ChannelParticipantCreator))

                if is_admin:
                    logger.info(f"[{self.profile_name}] ✅ {account.name} является админом в {chat_link}")
                else:
                    logger.info(f"[{self.profile_name}] ℹ️ {account.name} не является админом в {chat_link}")

                return is_admin

            except Exception as e:
                logger.warning(f"[{self.profile_name}] ⚠️ Не удалось проверить статус админа {account.name}: {e}")
                return False

        except Exception as e:
            logger.error(f"[{self.profile_name}] ❌ Ошибка проверки статуса админа {account.name}: {e}")
            return False

    async def ensure_bot_admin_rights(self, chat_links: list) -> bool:
        """
        Проверяет, что бот является админом во всех указанных чатах
        """
        try:
            all_good = True

            for chat_link in chat_links:
                has_rights = await self.bot_manager.check_admin_rights(chat_link)
                if not has_rights:
                    logger.error(
                        f"[{self.profile_name}] ❌ Бот @{self.bot_manager.bot_username} НЕ является админом в {chat_link}")
                    all_good = False

            if all_good:
                logger.info(
                    f"[{self.profile_name}] ✅ Бот @{self.bot_manager.bot_username} является админом во всех чатах")
            else:
                logger.error(
                    f"[{self.profile_name}] ❌ Бот @{self.bot_manager.bot_username} не имеет прав админа в некоторых чатах")

            return all_good

        except Exception as e:
            logger.error(f"[{self.profile_name}] ❌ Ошибка проверки прав бота во всех чатах: {e}")
            return False