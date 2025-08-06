# src/modules/impl/inviter/admin_rights_manager.py
"""
ИСПРАВЛЕННЫЙ Менеджер управления правами администраторов
Бот только выдает/забирает права главному админу
Главный админ сам управляет правами воркеров
"""

import asyncio
from typing import Dict, Set, Optional, List
from datetime import datetime, timedelta
from loguru import logger

from .bot_manager import BotManager

# Импорты Telethon для прямого управления правами
from telethon.tl.functions.channels import EditAdminRequest
from telethon.tl.types import ChatAdminRights


class AdminRightsManager:
    """ИСПРАВЛЕННЫЙ менеджер - только для главного админа, воркеры управляются напрямую"""

    def __init__(self, bot_manager: BotManager):
        self.bot_manager = bot_manager

        # Отслеживаем только главных админов
        # Format: {chat_link: {'user_id': int, 'account_name': str, 'granted_at': datetime}}
        self.main_admins: Dict[str, Dict] = {}

        # Блокировки для потокобезопасности
        self._locks: Dict[str, asyncio.Lock] = {}

    def _get_lock(self, chat_link: str) -> asyncio.Lock:
        """Получает lock для конкретного чата"""
        if chat_link not in self._locks:
            self._locks[chat_link] = asyncio.Lock()
        return self._locks[chat_link]

    async def grant_main_admin_rights(self, chat_link: str, user_id: int, account_name: str) -> bool:
        """
        ТОЛЬКО выдает права главному админу через бота

        Args:
            chat_link: Ссылка на чат
            user_id: ID главного админа
            account_name: Имя аккаунта главного админа

        Returns:
            bool: True если права выданы успешно
        """
        async with self._get_lock(chat_link):
            try:

                # Выдаем права через бота
                success = await self.bot_manager.grant_admin_rights(chat_link, user_id)

                if success:
                    # Сохраняем информацию о главном админе
                    self.main_admins[chat_link] = {
                        'user_id': user_id,
                        'account_name': account_name,
                        'granted_at': datetime.now()
                    }

                    logger.success(f"✅ Главный админ {account_name} получил права в {chat_link} через БОТА")
                    return True
                else:
                    logger.error(f"❌ Не удалось выдать права главному админу {account_name} через бота")
                    return False

            except Exception as e:
                logger.error(f"❌ Ошибка выдачи прав главному админу {account_name}: {e}")
                return False

    async def revoke_main_admin_rights(self, chat_link: str) -> bool:
        """
        ТОЛЬКО забирает права у главного админа через бота

        Args:
            chat_link: Ссылка на чат

        Returns:
            bool: True если права забраны успешно
        """
        async with self._get_lock(chat_link):
            try:
                main_admin = self.main_admins.get(chat_link)
                if not main_admin:
                    logger.warning(f"⚠️ Нет главного админа для отзыва прав в {chat_link}")
                    return True

                user_id = main_admin['user_id']
                account_name = main_admin['account_name']

                logger.info(f"👑🔒 Отзыв прав у главного админа через БОТА: {account_name} (ID: {user_id}) в {chat_link}")

                # Забираем права через бота
                success = await self.bot_manager.revoke_admin_rights(chat_link, user_id)

                if success:
                    # Удаляем из отслеживания
                    del self.main_admins[chat_link]
                    logger.success(f"✅ Права отозваны у главного админа {account_name} в {chat_link} через БОТА")
                    return True
                else:
                    logger.warning(f"⚠️ Не удалось отозвать права у главного админа {account_name} через бота")
                    return False

            except Exception as e:
                logger.error(f"❌ Ошибка отзыва прав у главного админа в {chat_link}: {e}")
                return False

    def get_main_admin(self, chat_link: str) -> Optional[Dict]:
        """Возвращает информацию о главном админе в чате"""
        return self.main_admins.get(chat_link)

    def is_main_admin_active(self, chat_link: str) -> bool:
        """Проверяет, активен ли главный админ в чате"""
        return chat_link in self.main_admins

    def get_stats(self) -> Dict:
        """Возвращает статистику по правам"""
        return {
            'main_admins_count': len(self.main_admins),
            'active_chats': len(self.main_admins)
        }


# НОВЫЕ ФУНКЦИИ: Прямое управление правами воркеров через главного админа
async def grant_worker_rights_directly(main_admin, chat_entity, worker_user_id: int, worker_user_access_hash: int,
                                       worker_name: str) -> bool:
    """
    Напрямую выдает права потоку через админа
    """
    try:
        from telethon.tl.functions.channels import EditAdminRequest, GetParticipantRequest
        from telethon.tl.types import ChatAdminRights, InputUser, InputPeerUser
        from telethon.errors import UserNotParticipantError, UserIdInvalidError

        participants_checked = 0

        # БЕЗ ЛИМИТА - получаем ВСЕХ участников
        async for participant in main_admin.client.iter_participants(chat_entity):
            participants_checked += 1

            if participant.id == worker_user_id:
                logger.info(f"✅ НАЙДЕН {worker_name} на позиции {participants_checked}")

                # Используем актуальный access_hash из группы
                actual_access_hash = participant.access_hash

                # Проверяем участие через GetParticipantRequest
                worker_peer = InputPeerUser(user_id=worker_user_id, access_hash=actual_access_hash)
                await main_admin.client(GetParticipantRequest(channel=chat_entity, participant=worker_peer))

                # Выдаем права
                worker_input = InputUser(user_id=worker_user_id, access_hash=actual_access_hash)
                rights = ChatAdminRights(invite_users=True, add_admins=True, anonymous=True)

                await main_admin.client(EditAdminRequest(
                    channel=chat_entity,
                    user_id=worker_input,
                    admin_rights=rights,
                    rank="админ"
                ))

                return True

        # Если дошли сюда - пользователь не найден
        logger.error(f"❌ {worker_name} НЕ НАЙДЕН среди {participants_checked} участников")
        return False

    except Exception as e:
        logger.error(f"❌ Ошибка для {worker_name}: {e}")
        return False


async def revoke_worker_rights_directly(main_admin_client, chat_entity, worker_user_id: int, worker_name: str) -> bool:
    """
    Забирает права у воркера напрямую через главного админа

    Args:
        main_admin_client: Клиент главного админа (Telethon)
        chat_entity: Entity чата
        worker_user_id: ID воркера
        worker_name: Имя воркера для логов

    Returns:
        bool: True если права забраны
    """
    try:

        input_user = await main_admin_client.get_input_entity(worker_user_id)

        # Убираем все права (ChatAdminRights с False по всем полям)
        no_rights = ChatAdminRights(
            invite_users=False,
            add_admins=False,
            ban_users=False,
            delete_messages=False,
            edit_messages=False,
            post_messages=False,
            pin_messages=False,
            manage_call=False,
            other=False,
            anonymous=False
        )

        # Забираем права через главного админа
        await main_admin_client(EditAdminRequest(
            channel=chat_entity,
            user_id=input_user,
            admin_rights=no_rights,
            rank=""  # Убираем звание
        ))

        return True

    except Exception as e:
        logger.error(f"❌ Ошибка отзыва прав у воркера {worker_name} главным админом: {e}")
        return False