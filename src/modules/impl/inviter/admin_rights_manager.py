# src/modules/impl/inviter/admin_rights_manager.py
"""
Менеджер для управления правами администратора
"""

import asyncio
from typing import Dict, Set
from loguru import logger

from .bot_manager import BotManager


class AdminRightsManager:
    """Менеджер для выдачи и отзыва прав администратора"""

    def __init__(self, bot_manager: BotManager, profile_name: str):
        self.bot_manager = bot_manager
        self.profile_name = profile_name

        # Отслеживание выданных прав
        # Структура: {chat_link: {account_name: bool}}
        self.granted_rights: Dict[str, Set[str]] = {}

        # Статистика
        self.total_grants = 0
        self.total_revokes = 0
        self.failed_grants = 0
        self.failed_revokes = 0

    async def grant_admin_rights(
            self,
            account,
            chat_link: str,
            max_retries: int = 3,
            retry_delay: float = 2.0
    ) -> bool:
        """
        Выдает права администратора аккаунту

        Args:
            account: Аккаунт которому выдаем права
            chat_link: Ссылка на чат
            max_retries: Максимальное количество попыток
            retry_delay: Задержка между попытками

        Returns:
            True если права выданы успешно
        """
        account_name = account.name

        # Проверяем не выданы ли уже права
        if self._has_admin_rights(chat_link, account_name):
            logger.debug(f"[{self.profile_name}] ℹ️ Права уже выданы: {account_name} → {chat_link}")
            return True

        logger.info(f"[{self.profile_name}] 🔧 Выдача прав админа: {account_name} → {chat_link}")

        for attempt in range(1, max_retries + 1):
            try:
                success = await self.bot_manager.promote_account_to_admin(account, chat_link)

                if success:
                    # Записываем выданные права
                    self._mark_admin_rights_granted(chat_link, account_name)
                    self.total_grants += 1

                    logger.info(f"[{self.profile_name}] ✅ Права админа выданы (попытка {attempt}): {account_name}")
                    return True
                else:
                    logger.warning(
                        f"[{self.profile_name}] ⚠️ Не удалось выдать права (попытка {attempt}): {account_name}")

                    if attempt < max_retries:
                        await asyncio.sleep(retry_delay)
                        continue
                    else:
                        self.failed_grants += 1
                        return False

            except Exception as e:
                logger.error(f"[{self.profile_name}] ❌ Ошибка выдачи прав (попытка {attempt}): {account_name}: {e}")

                if attempt < max_retries:
                    await asyncio.sleep(retry_delay)
                    continue
                else:
                    self.failed_grants += 1
                    return False

        self.failed_grants += 1
        return False

    async def revoke_admin_rights(
            self,
            account,
            chat_link: str,
            max_retries: int = 2,
            retry_delay: float = 1.0
    ) -> bool:
        """
        Отзывает права администратора у аккаунта

        Args:
            account: Аккаунт у которого отзываем права
            chat_link: Ссылка на чат
            max_retries: Максимальное количество попыток
            retry_delay: Задержка между попытками

        Returns:
            True если права отозваны успешно
        """
        account_name = account.name

        # Проверяем были ли выданы права
        if not self._has_admin_rights(chat_link, account_name):
            logger.debug(f"[{self.profile_name}] ℹ️ Права не были выданы: {account_name} ← {chat_link}")
            return True

        logger.info(f"[{self.profile_name}] 🔄 Отзыв прав админа: {account_name} ← {chat_link}")

        for attempt in range(1, max_retries + 1):
            try:
                success = await self.bot_manager.revoke_admin_rights(account, chat_link)

                if success:
                    # Записываем отзыв прав
                    self._mark_admin_rights_revoked(chat_link, account_name)
                    self.total_revokes += 1

                    logger.info(f"[{self.profile_name}] ✅ Права админа отозваны (попытка {attempt}): {account_name}")
                    return True
                else:
                    logger.warning(
                        f"[{self.profile_name}] ⚠️ Не удалось отозвать права (попытка {attempt}): {account_name}")

                    if attempt < max_retries:
                        await asyncio.sleep(retry_delay)
                        continue
                    else:
                        # Даже если не удалось отозвать, помечаем как отозванные
                        # чтобы не пытаться отзывать повторно
                        self._mark_admin_rights_revoked(chat_link, account_name)
                        self.failed_revokes += 1
                        logger.warning(
                            f"[{self.profile_name}] ⚠️ Права помечены как отозванные принудительно: {account_name}")
                        return False

            except Exception as e:
                logger.error(f"[{self.profile_name}] ❌ Ошибка отзыва прав (попытка {attempt}): {account_name}: {e}")

                if attempt < max_retries:
                    await asyncio.sleep(retry_delay)
                    continue
                else:
                    # Помечаем как отозванные даже при ошибке
                    self._mark_admin_rights_revoked(chat_link, account_name)
                    self.failed_revokes += 1
                    return False

        self.failed_revokes += 1
        return False

    async def revoke_all_granted_rights(self, chat_link: str) -> Dict[str, bool]:
        """
        Отзывает все выданные права в конкретном чате

        Args:
            chat_link: Ссылка на чат

        Returns:
            Словарь {account_name: success}
        """
        if chat_link not in self.granted_rights:
            logger.debug(f"[{self.profile_name}] ℹ️ Нет выданных прав в чате: {chat_link}")
            return {}

        account_names = list(self.granted_rights[chat_link])
        results = {}

        logger.info(f"[{self.profile_name}] 🔄 Отзыв всех прав в чате {chat_link}: {len(account_names)} аккаунтов")

        for account_name in account_names:
            try:
                # Тут нужен объект аккаунта, но у нас только имя
                # Это ограничение - нужно передавать объект аккаунта
                logger.warning(f"[{self.profile_name}] ⚠️ Не можем отозвать права без объекта аккаунта: {account_name}")
                results[account_name] = False
            except Exception as e:
                logger.error(f"[{self.profile_name}] ❌ Ошибка отзыва всех прав для {account_name}: {e}")
                results[account_name] = False

        return results

    def _has_admin_rights(self, chat_link: str, account_name: str) -> bool:
        """Проверяет выданы ли права аккаунту в чате"""
        return (chat_link in self.granted_rights and
                account_name in self.granted_rights[chat_link])

    def _mark_admin_rights_granted(self, chat_link: str, account_name: str):
        """Помечает права как выданные"""
        if chat_link not in self.granted_rights:
            self.granted_rights[chat_link] = set()

        self.granted_rights[chat_link].add(account_name)
        logger.debug(f"[{self.profile_name}] 📝 Права помечены как выданные: {account_name} → {chat_link}")

    def _mark_admin_rights_revoked(self, chat_link: str, account_name: str):
        """Помечает права как отозванные"""
        if chat_link in self.granted_rights:
            self.granted_rights[chat_link].discard(account_name)

            # Если в чате больше нет аккаунтов с правами - удаляем чат
            if not self.granted_rights[chat_link]:
                del self.granted_rights[chat_link]

        logger.debug(f"[{self.profile_name}] 📝 Права помечены как отозванные: {account_name} ← {chat_link}")

    def get_granted_rights_count(self) -> int:
        """Возвращает общее количество выданных прав"""
        total = 0
        for chat_accounts in self.granted_rights.values():
            total += len(chat_accounts)
        return total

    def get_stats(self) -> Dict:
        """Возвращает статистику работы"""
        return {
            'total_grants': self.total_grants,
            'total_revokes': self.total_revokes,
            'failed_grants': self.failed_grants,
            'failed_revokes': self.failed_revokes,
            'currently_granted': self.get_granted_rights_count(),
            'active_chats': len(self.granted_rights)
        }

    def print_stats(self):
        """Выводит статистику в лог"""
        stats = self.get_stats()

        logger.info(f"[{self.profile_name}] 📊 СТАТИСТИКА АДМИН-ПРАВ:")
        logger.info(f"   ✅ Выдано прав: {stats['total_grants']}")
        logger.info(f"   🔄 Отозвано прав: {stats['total_revokes']}")
        logger.info(f"   ❌ Ошибок выдачи: {stats['failed_grants']}")
        logger.info(f"   ❌ Ошибок отзыва: {stats['failed_revokes']}")
        logger.info(f"   🔧 Активных прав: {stats['currently_granted']}")
        logger.info(f"   💬 Активных чатов: {stats['active_chats']}")

        # Показываем детали по чатам
        if self.granted_rights:
            logger.info(f"[{self.profile_name}] 📋 ДЕТАЛИ ПО ЧАТАМ:")
            for chat_link, accounts in self.granted_rights.items():
                logger.info(f"   🔗 {chat_link}: {len(accounts)} аккаунтов с правами")
                for account_name in list(accounts)[:3]:  # Показываем только первые 3
                    logger.info(f"      - {account_name}")
                if len(accounts) > 3:
                    logger.info(f"      ... и еще {len(accounts) - 3}")

    def clear_all_tracking(self):
        """Очищает все отслеживание прав (для экстренных случаев)"""
        logger.warning(f"[{self.profile_name}] 🧹 Очистка всего отслеживания админ-прав")
        self.granted_rights.clear()

    def __str__(self):
        return f"AdminRightsManager({self.profile_name}, {self.get_granted_rights_count()} прав)"

    def __repr__(self):
        return self.__str__()