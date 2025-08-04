# src/modules/impl/inviter/bot_manager.py

import os
import asyncio
from typing import Optional, Dict, Any
from loguru import logger
from pathlib import Path

from .bot_base import BotBase
from .bot_creator import get_or_create_bot_for_account


class BotManager:
    """
    Менеджер для работы с ботом в админ-инвайте.
    Использует твою систему: проверяет JSON -> создает бота если нужно.
    """

    def __init__(self, account_name: str, profile_name: str):
        self.account_name = account_name
        self.profile_name = profile_name

        # Данные бота
        self.bot_account = None  # Account для создания/управления ботом
        self.bot_base: Optional[BotBase] = None
        self.bot_token: Optional[str] = None
        self.bot_username: Optional[str] = None

        # Флаги состояния
        self.is_initialized = False
        self.is_connected = False

    async def initialize(self) -> bool:
        """
        Инициализирует бота: загружает аккаунт, получает/создает бота, создает BotBase
        """
        try:
            logger.info(f"[{self.profile_name}] 🤖 Инициализация бот-менеджера...")

            # 1. Загружаем аккаунт из папки bot_holders
            self.bot_account = await self._load_bot_holder_account()
            if not self.bot_account:
                logger.error(f"[{self.profile_name}] ❌ Не удалось загрузить бот-аккаунт {self.account_name}")
                return False

            logger.info(f"[{self.profile_name}] ✅ Бот-аккаунт загружен: {self.account_name}")

            # 2. Получаем/создаем бота через твою систему
            bot_data = await get_or_create_bot_for_account(self.bot_account)
            if not bot_data:
                logger.error(f"[{self.profile_name}] ❌ Не удалось получить/создать бота")
                return False

            self.bot_token = bot_data['token']
            self.bot_username = bot_data['username']

            logger.info(f"[{self.profile_name}] ✅ Данные бота получены: @{self.bot_username}")

            # 3. Создаем BotBase ТОЛЬКО с aiogram
            self.bot_base = await self._create_bot_base()
            if not self.bot_base:
                logger.error(f"[{self.profile_name}] ❌ Не удалось создать BotBase")
                return False

            # 4. Подключаемся через aiogram
            if not await self.bot_base.connect():
                logger.error(f"[{self.profile_name}] ❌ Не удалось подключить бота")
                return False

            self.is_initialized = True
            self.is_connected = True

            # 5. Отключаем Account после инициализации (больше не нужен для управления)
            await self.bot_account.disconnect()
            logger.info(f"[{self.profile_name}] 🔌 Account отключен (бот инициализирован)")

            logger.info(f"[{self.profile_name}] 🎉 Бот-менеджер успешно инициализирован!")

            return True

        except Exception as e:
            logger.error(f"[{self.profile_name}] ❌ Ошибка инициализации бот-менеджера: {e}")
            return False

    async def _load_bot_holder_account(self):
        """Загружает аккаунт из папки bot_holders"""
        try:
            from paths import BOT_HOLDERS_FOLDER
            from src.accounts.impl.account import Account

            session_path = BOT_HOLDERS_FOLDER / f"{self.account_name}.session"
            json_path = BOT_HOLDERS_FOLDER / f"{self.account_name}.json"

            if not session_path.exists() or not json_path.exists():
                logger.error(f"[{self.profile_name}] ❌ Файлы аккаунта не найдены: {self.account_name}")
                return None

            # Создаем объект Account
            account = Account(session_path, json_path)

            # Создаем клиент и подключаемся (нужно для работы с BotFather)
            await account.create_client()
            if not await account.connect():
                logger.error(f"[{self.profile_name}] ❌ Не удалось подключить аккаунт {self.account_name}")
                return None

            return account

        except Exception as e:
            logger.error(f"[{self.profile_name}] ❌ Ошибка загрузки бот-аккаунта: {e}")
            return None

    async def _create_bot_base(self) -> Optional[BotBase]:
        """Создает BotBase ТОЛЬКО с aiogram (без Telethon)"""
        try:
            # Получаем прокси для аккаунта (может быть None)
            from src.proxies.manager import get_proxy_for_account
            proxy_config = get_proxy_for_account(self.account_name)

            # Создаем BotBase ТОЛЬКО с aiogram
            bot_base = BotBase(
                bot_username=self.bot_username,
                bot_token=self.bot_token,
                proxy_config=proxy_config
            )

            return bot_base

        except Exception as e:
            logger.error(f"[{self.profile_name}] ❌ Ошибка создания BotBase: {e}")
            return None

    async def check_admin_rights(self, chat_link: str) -> bool:
        """Проверяет, является ли бот админом в указанном чате"""
        try:
            if not self.bot_base or not self.is_initialized:
                logger.error(f"[{self.profile_name}] ❌ Бот не инициализирован")
                return False

            return await self.bot_base.has_self_admin(chat_link)

        except Exception as e:
            logger.error(f"[{self.profile_name}] ❌ Ошибка проверки прав бота в {chat_link}: {e}")
            return False

    async def grant_admin_rights(self, account, chat_link: str) -> bool:
        """
        Выдает права админа указанному аккаунту в чате.
        account - это объект Account с Telethon клиентом для получения данных.
        """
        try:
            if not self.bot_base or not self.is_initialized:
                logger.error(f"[{self.profile_name}] ❌ Бот не инициализирован")
                return False

            logger.info(f"[{self.profile_name}] 🔧 Выдаем права админа аккаунту {account.name} в {chat_link}")

            # Передаем аккаунт в BotBase - он использует его Telethon для получения данных
            result = await self.bot_base.grant_admin(
                acc=account,  # Account с Telethon клиентом
                link=chat_link,
                can_invite_users=True,
                can_delete_messages=True,
                can_pin_messages=True,
                can_change_info=True,
                can_manage_video_chats=True,
                can_post_messages=True,
                rank=""
            )

            if result:
                logger.info(f"[{self.profile_name}] ✅ Права админа выданы: {account.name} в {chat_link}")
            else:
                logger.error(f"[{self.profile_name}] ❌ Не удалось выдать права админа: {account.name} в {chat_link}")

            return result

        except Exception as e:
            logger.error(f"[{self.profile_name}] ❌ Ошибка выдачи прав админа {account.name} в {chat_link}: {e}")
            return False

    async def revoke_admin_rights(self, account, chat_link: str) -> bool:
        """
        Отзывает права админа у указанного аккаунта в чате.
        account - это объект Account с Telethon клиентом для получения данных.
        """
        try:
            if not self.bot_base or not self.is_initialized:
                logger.error(f"[{self.profile_name}] ❌ Бот не инициализирован")
                return False

            logger.info(f"[{self.profile_name}] 🔄 Отзываем права админа у аккаунта {account.name} в {chat_link}")

            # Передаем аккаунт в BotBase - он использует его Telethon для получения данных
            result = await self.bot_base.revoke_admin(
                acc=account,  # Account с Telethon клиентом
                link=chat_link
            )

            if result:
                logger.info(f"[{self.profile_name}] ✅ Права админа отозваны: {account.name} в {chat_link}")
            else:
                logger.warning(
                    f"[{self.profile_name}] ⚠️ Не удалось отозвать права (возможно, уже нет прав): {account.name} в {chat_link}")

            return result

        except Exception as e:
            logger.error(f"[{self.profile_name}] ❌ Ошибка отзыва прав админа {account.name} в {chat_link}: {e}")
            return False

    async def get_bot_info(self) -> Optional[Dict[str, Any]]:
        """Возвращает информацию о боте"""
        try:
            if not self.bot_base or not self.is_initialized:
                return None

            me = await self.bot_base.api.get_me()
            return {
                'id': me.id,
                'username': me.username,
                'first_name': me.first_name,
                'is_bot': me.is_bot
            }

        except Exception as e:
            logger.error(f"[{self.profile_name}] ❌ Ошибка получения информации о боте: {e}")
            return None

    async def close(self):
        """Закрывает соединения"""
        try:
            if self.bot_base:
                await self.bot_base.disconnect()
                logger.info(f"[{self.profile_name}] 🔌 Соединения бота закрыты")

        except Exception as e:
            logger.error(f"[{self.profile_name}] ❌ Ошибка закрытия соединений бота: {e}")

        finally:
            self.is_connected = False
            self.is_initialized = False