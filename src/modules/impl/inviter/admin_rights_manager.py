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

    async def revoke_main_admin_rights(self, chat_link: str, user_id: int, account_name: str) -> bool:
        """
        🔥 ИСПРАВЛЕНО: ТОЛЬКО забирает права у главного админа через бота (точно как grant_main_admin_rights только наоборот)

        Args:
            chat_link: Ссылка на чат
            user_id: ID главного админа
            account_name: Имя аккаунта главного админа

        Returns:
            bool: True если права забраны успешно
        """
        async with self._get_lock(chat_link):
            try:

                # Забираем права через бота
                success = await self.bot_manager.revoke_admin_rights(chat_link, user_id)

                if success:
                    # Удаляем из отслеживания
                    if chat_link in self.main_admins:
                        del self.main_admins[chat_link]

                    logger.debug(f"✅ Права отозваны у главного админа {account_name} в {chat_link} через БОТА")
                    return True
                else:
                    logger.error(f"❌ Не удалось отозвать права у главного админа {account_name} через бота")
                    return False

            except Exception as e:
                logger.error(f"❌ Ошибка отзыва прав у главного админа {account_name}: {e}")
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
                                       worker_name: str, worker_username: str, chat_link) -> bool | str:
    """
    Напрямую выдает права потоку через админа с повторными попытками
    """
    max_retries = 3
    retry_delay = 10  # секунд

    for attempt in range(max_retries):
        try:
            from telethon.tl.functions.channels import EditAdminRequest, GetParticipantRequest
            from telethon.tl.types import ChatAdminRights, InputUser, InputPeerUser
            from telethon.errors import UserNotParticipantError, UsernameNotOccupiedError

            # --- Точечный поиск по username (без полного перебора) ---
            uname = (worker_username or "").lstrip("@").strip()
            if not uname:
                logger.error("❌ Пустой username")
                return False

            try:
                # получаем юзера по username
                user = await main_admin.client.get_entity(uname)  # tl.types.User
            except (UsernameNotOccupiedError, ValueError):
                logger.error(f"❌ @{uname} не существует или недоступен")
                return False

            # выдаём права (НЕ меняю набор прав)
            worker_input = InputUser(user_id=user.id, access_hash=user.access_hash)
            rights = ChatAdminRights(invite_users=True, add_admins=True, anonymous=True)

            await main_admin.client(EditAdminRequest(
                channel=chat_entity,
                user_id=worker_input,
                admin_rights=rights,
                rank="админ"
            ))

            return True

        except Exception as e:
            error_message = str(e).lower()

            # Проверяем, содержит ли ошибка нужный текст
            if "chat admin privileges are required to do that in the specified chat" in error_message:
                if attempt < max_retries - 1:  # Если это не последняя попытка
                    logger.warning(f"⚠️ Попытка {attempt + 1}/{max_retries} для {worker_name}: {e}")
                    logger.info(f"🔄 Повторная попытка через {retry_delay} секунд...")
                    await asyncio.sleep(retry_delay)
                    continue
                else:
                    logger.error(f"❌ Все {max_retries} попытки исчерпаны для {worker_name}: {e}")
                    return False
            elif "Too many admins" in error_message:
                logger.error(f"❌ Главный админ  {main_admin.name} сообщает: В чате {chat_link} много админов")
                return "TOO_MANY_ADMINS"
            else:
                # Если это другая ошибка, не повторяем
                logger.error(f"❌ Ошибка для {worker_name}: {e}")
                return False

    # Этот код никогда не должен выполниться, но на всякий случай
    return False



async def revoke_worker_rights_directly(main_admin_client, chat_entity, worker_user_id: int, worker_name: str, worker_username: str) -> bool:
    """
    Забирает права у воркера напрямую через главного админа
    """
    try:
        from telethon.tl.functions.channels import EditAdminRequest, GetParticipantRequest
        from telethon.tl.types import ChatAdminRights, InputUser, InputPeerUser
        from telethon.errors import UserNotParticipantError, UsernameNotOccupiedError

        # --- Точечный поиск по username ---
        uname = (worker_username or "").lstrip("@").strip()
        if not uname:
            logger.error("❌ Пустой username")
            return False

        try:
            user = await main_admin_client.get_entity(uname)  # tl.types.User
        except (UsernameNotOccupiedError, ValueError):
            logger.error(f"❌ @{uname} не существует или недоступен через get_entity()")
            return False

        # Проверяем, что пользователь состоит в чате/канале
        '''try:
            worker_peer = InputPeerUser(user_id=user.id, access_hash=user.access_hash)
            await main_admin_client(GetParticipantRequest(channel=chat_entity, participant=worker_peer))
        except UserNotParticipantError:
            logger.error(f"❌ {worker_name} (@{uname}) не является участником чата")
            return False'''

        # Убираем все права (оставляю набор полей как в твоём коде)
        no_rights = ChatAdminRights(
            invite_users=False,
            add_admins=False,
            anonymous=False
        )

        # Адресно снимаем права
        input_user = InputUser(user_id=user.id, access_hash=user.access_hash)
        await main_admin_client(EditAdminRequest(
            channel=chat_entity,
            user_id=input_user,
            admin_rights=no_rights,
            rank=""  # убрать звание
        ))

        logger.debug(f"✅ Права сняты с {worker_name} (@{uname})")
        return True

    except Exception as e:
        logger.error(f"❌ Ошибка отзыва прав у воркера {worker_name}: {e}")
        return False