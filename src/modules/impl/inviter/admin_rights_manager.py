# src/modules/impl/inviter/admin_rights_manager.py
"""
Менеджер управления правами администраторов
Отслеживает кто получил права, управляет выдачей/отзывом прав
"""

import asyncio
from typing import Dict, Set, Optional, List
from datetime import datetime, timedelta
from loguru import logger

from .bot_manager import BotManager


class AdminRightsManager:
    """Менеджер управления правами администраторов в чатах"""

    def __init__(self, bot_manager: BotManager):
        self.bot_manager = bot_manager

        # Отслеживаем права по чатам
        # Format: {chat_link: {user_id: {'granted_at': datetime, 'account_name': str}}}
        self.granted_rights: Dict[str, Dict[int, Dict]] = {}

        # Главные админы по чатам
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
        Выдает права главного админа

        Args:
            chat_link: Ссылка на чат
            user_id: ID пользователя
            account_name: Имя аккаунта

        Returns:
            bool: True если права выданы успешно
        """
        print('dsfdsfdsfdsfdsfsfs')
        async with self._get_lock(chat_link):
            try:
                logger.info(f"👑 Выдача прав главного админа: {account_name} (ID: {user_id}) в {chat_link}")

                # Проверяем, что бот сам является админом
                if not await self.bot_manager.check_bot_admin_status(chat_link):
                    logger.error(f"❌ Бот не является админом в {chat_link}")
                    return False

                # Выдаем права через бота
                success = await self.bot_manager.grant_admin_rights(chat_link, user_id)

                if success:
                    # Сохраняем информацию о главном админе
                    self.main_admins[chat_link] = {
                        'user_id': user_id,
                        'account_name': account_name,
                        'granted_at': datetime.now()
                    }

                    # Также добавляем в общий список прав
                    if chat_link not in self.granted_rights:
                        self.granted_rights[chat_link] = {}

                    self.granted_rights[chat_link][user_id] = {
                        'granted_at': datetime.now(),
                        'account_name': account_name,
                        'is_main_admin': True
                    }

                    logger.info(f"✅ Главный админ {account_name} получил права в {chat_link}")
                    return True
                else:
                    logger.error(f"❌ Не удалось выдать права главному админу {account_name}")
                    return False

            except Exception as e:
                logger.error(f"❌ Ошибка выдачи прав главному админу {account_name}: {e}")
                return False

    async def grant_worker_rights(self, chat_link: str, user_id: int, account_name: str) -> bool:
        """
        Выдает права воркеру (через главного админа)

        Args:
            chat_link: Ссылка на чат
            user_id: ID пользователя-воркера
            account_name: Имя аккаунта-воркера

        Returns:
            bool: True если права выданы успешно
        """
        async with self._get_lock(chat_link):
            try:
                logger.info(f"👷 Выдача прав воркеру: {account_name} (ID: {user_id}) в {chat_link}")

                # Проверяем, что есть главный админ в этом чате
                main_admin = self.main_admins.get(chat_link)
                if not main_admin:
                    logger.error(f"❌ Нет главного админа в чате {chat_link}")
                    return False

                # Выдаем права через бота (у главного админа уже есть права на это)
                success = await self.bot_manager.grant_admin_rights(chat_link, user_id)

                if success:
                    # Сохраняем информацию о воркере
                    if chat_link not in self.granted_rights:
                        self.granted_rights[chat_link] = {}

                    self.granted_rights[chat_link][user_id] = {
                        'granted_at': datetime.now(),
                        'account_name': account_name,
                        'is_main_admin': False
                    }

                    logger.info(f"✅ Воркер {account_name} получил права в {chat_link}")
                    return True
                else:
                    logger.error(f"❌ Не удалось выдать права воркеру {account_name}")
                    return False

            except Exception as e:
                logger.error(f"❌ Ошибка выдачи прав воркеру {account_name}: {e}")
                return False

    async def revoke_worker_rights(self, chat_link: str, user_id: int, account_name: str) -> bool:
        """
        Забирает права у воркера

        Args:
            chat_link: Ссылка на чат
            user_id: ID пользователя-воркера
            account_name: Имя аккаунта-воркера

        Returns:
            bool: True если права забраны успешно
        """
        async with self._get_lock(chat_link):
            try:
                logger.info(f"🔒 Отзыв прав у воркера: {account_name} (ID: {user_id}) в {chat_link}")

                # Забираем права через бота
                success = await self.bot_manager.revoke_admin_rights(chat_link, user_id)

                if success:
                    # Удаляем из отслеживания
                    if chat_link in self.granted_rights and user_id in self.granted_rights[chat_link]:
                        del self.granted_rights[chat_link][user_id]

                    logger.info(f"✅ Права отозваны у воркера {account_name} в {chat_link}")
                    return True
                else:
                    logger.warning(f"⚠️ Не удалось отозвать права у воркера {account_name}")
                    return False

            except Exception as e:
                logger.error(f"❌ Ошибка отзыва прав у воркера {account_name}: {e}")
                return False

    async def revoke_main_admin_rights(self, chat_link: str) -> bool:
        """
        Забирает права у главного админа

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

                logger.info(f"👑🔒 Отзыв прав у главного админа: {account_name} (ID: {user_id}) в {chat_link}")

                # Забираем права через бота
                success = await self.bot_manager.revoke_admin_rights(chat_link, user_id)

                if success:
                    # Удаляем из отслеживания
                    if chat_link in self.main_admins:
                        del self.main_admins[chat_link]

                    if chat_link in self.granted_rights and user_id in self.granted_rights[chat_link]:
                        del self.granted_rights[chat_link][user_id]

                    logger.info(f"✅ Права отозваны у главного админа {account_name} в {chat_link}")
                    return True
                else:
                    logger.warning(f"⚠️ Не удалось отозвать права у главного админа {account_name}")
                    return False

            except Exception as e:
                logger.error(f"❌ Ошибка отзыва прав у главного админа в {chat_link}: {e}")
                return False

    async def cleanup_chat_rights(self, chat_link: str) -> bool:
        """
        Очищает все права в чате (воркеры + главный админ)

        Args:
            chat_link: Ссылка на чат

        Returns:
            bool: True если очистка прошла успешно
        """
        async with self._get_lock(chat_link):
            try:
                logger.info(f"🧹 Очистка всех прав в чате {chat_link}")

                success_count = 0
                total_count = 0

                # Забираем права у всех воркеров
                chat_rights = self.granted_rights.get(chat_link, {})
                for user_id, user_info in chat_rights.copy().items():
                    if not user_info.get('is_main_admin', False):
                        total_count += 1
                        if await self.revoke_worker_rights(chat_link, user_id, user_info['account_name']):
                            success_count += 1

                # Забираем права у главного админа
                if chat_link in self.main_admins:
                    total_count += 1
                    if await self.revoke_main_admin_rights(chat_link):
                        success_count += 1

                # Очищаем все записи для этого чата
                if chat_link in self.granted_rights:
                    del self.granted_rights[chat_link]

                logger.info(f"✅ Очистка прав завершена для {chat_link}: {success_count}/{total_count} успешно")
                return success_count == total_count

            except Exception as e:
                logger.error(f"❌ Ошибка очистки прав в чате {chat_link}: {e}")
                return False

    def get_chat_admins(self, chat_link: str) -> Dict[int, Dict]:
        """Возвращает всех админов в указанном чате"""
        return self.granted_rights.get(chat_link, {})

    def get_main_admin(self, chat_link: str) -> Optional[Dict]:
        """Возвращает информацию о главном админе в чате"""
        return self.main_admins.get(chat_link)

    def is_main_admin_active(self, chat_link: str) -> bool:
        """Проверяет, активен ли главный админ в чате"""
        return chat_link in self.main_admins

    def get_worker_count(self, chat_link: str) -> int:
        """Возвращает количество воркеров с правами в чате"""
        chat_rights = self.granted_rights.get(chat_link, {})
        return len([u for u in chat_rights.values() if not u.get('is_main_admin', False)])

    def get_stats(self) -> Dict:
        """Возвращает статистику по правам"""
        total_chats = len(self.granted_rights)
        total_admins = sum(len(rights) for rights in self.granted_rights.values())
        total_main_admins = len(self.main_admins)
        total_workers = total_admins - total_main_admins

        return {
            'total_chats_with_rights': total_chats,
            'total_admins': total_admins,
            'main_admins': total_main_admins,
            'workers': total_workers,
            'active_main_admins': len(self.main_admins)
        }