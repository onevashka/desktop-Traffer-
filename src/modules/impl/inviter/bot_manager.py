# src/modules/impl/inviter/bot_manager.py
"""
Менеджер для управления ботом
"""

import json
import asyncio
from typing import Optional, Dict
from pathlib import Path
from loguru import logger

from .bot_creator import BotCreator
from .enhanced_bot_base import InviterBot
from paths import BOT_HOLDERS_FOLDER


class BotManager:
    """Менеджер для создания и управления ботом"""

    def __init__(self, account_name: str, profile_name: str):
        self.account_name = account_name
        self.profile_name = profile_name
        self.account_path = BOT_HOLDERS_FOLDER / f"{account_name}.json"
        self.session_path = BOT_HOLDERS_FOLDER / f"{account_name}.session"

        # Данные бота
        self.bot_token: Optional[str] = None
        self.bot_username: Optional[str] = None

        # Объекты для работы
        self.bot_creator: Optional[BotCreator] = None
        self.inviter_bot: Optional[InviterBot] = None
        self.account = None  # Аккаунт-держатель бота

    async def initialize(self) -> bool:
        """Инициализирует бот-менеджер"""
        try:
            logger.info(f"🤖 Инициализация бот-менеджера для {self.account_name}")

            # 1. Загружаем аккаунт-держатель
            if not await self._load_bot_account():
                logger.error("❌ Не удалось загрузить аккаунт-держатель")
                return False

            # 2. Создаем/получаем бота
            if not await self._setup_bot():
                logger.error("❌ Не удалось настроить бота")
                return False

            # 3. Инициализируем InviterBot
            if not await self._initialize_inviter_bot():
                logger.error("❌ Не удалось инициализировать InviterBot")
                return False

            logger.info(f"✅ Бот-менеджер инициализирован: @{self.bot_username}")
            return True

        except Exception as e:
            logger.error(f"❌ Ошибка инициализации бот-менеджера: {e}")
            return False

    async def _load_bot_account(self) -> bool:
        """Загружает аккаунт-держатель бота"""
        try:
            if not self.session_path.exists() or not self.account_path.exists():
                logger.error(f"❌ Файлы аккаунта {self.account_name} не найдены в папке держателей ботов")
                return False

            # Создаем объект аккаунта
            from src.accounts.impl.account import Account
            self.account = Account(self.account_name, str(self.session_path))

            # Подключаемся
            if not await self.account.connect():
                logger.error(f"❌ Не удалось подключить аккаунт {self.account_name}")
                return False

            logger.info(f"✅ Аккаунт-держатель подключен: {self.account_name}")
            return True

        except Exception as e:
            logger.error(f"❌ Ошибка загрузки аккаунта-держателя: {e}")
            return False

    async def _setup_bot(self) -> bool:
        """Создает или получает существующего бота"""
        try:
            # Проверяем есть ли уже токен в JSON файле
            bot_data = self._load_bot_data()

            if bot_data and bot_data.get('bot_token') and bot_data.get('bot_username'):
                # Бот уже существует
                self.bot_token = bot_data['bot_token']
                self.bot_username = bot_data['bot_username']
                logger.info(f"🤖 Найден существующий бот: @{self.bot_username}")
                return True

            # Создаем нового бота
            logger.info(f"🤖 Создаем нового бота для аккаунта {self.account_name}")

            self.bot_creator = BotCreator()
            bot_data = await self.bot_creator.create_bot_via_botfather(
                account=self.account,
                profile_name=self.profile_name
            )

            if not bot_data:
                logger.error("❌ Не удалось создать бота")
                return False

            self.bot_token = bot_data['token']
            self.bot_username = bot_data['username']

            # Сохраняем данные бота
            self._save_bot_data(self.bot_token, self.bot_username)

            logger.info(f"✅ Бот создан: @{self.bot_username}")
            return True

        except Exception as e:
            logger.error(f"❌ Ошибка настройки бота: {e}")
            return False

    async def _initialize_inviter_bot(self) -> bool:
        """Инициализирует InviterBot для работы с API"""
        try:
            if not self.bot_token or not self.bot_username:
                logger.error("❌ Нет данных бота для инициализации")
                return False

            # Создаем InviterBot
            self.inviter_bot = InviterBot(
                bot_token=self.bot_token,
                bot_username=self.bot_username
            )

            # Инициализируем
            if not await self.inviter_bot.initialize():
                logger.error("❌ Не удалось инициализировать InviterBot")
                return False

            logger.info(f"✅ InviterBot инициализирован: @{self.bot_username}")
            return True

        except Exception as e:
            logger.error(f"❌ Ошибка инициализации InviterBot: {e}")
            return False

    def _load_bot_data(self) -> Optional[Dict]:
        """Загружает данные бота из JSON файла"""
        try:
            if self.account_path.exists():
                with open(self.account_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки данных бота: {e}")
        return None

    def _save_bot_data(self, token: str, username: str):
        """Сохраняет данные бота в JSON файл"""
        try:
            # Загружаем существующие данные
            if self.account_path.exists():
                with open(self.account_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                data = {}

            # Добавляем данные бота
            data.update({
                'bot_token': token,
                'bot_username': username,
                'bot_created_at': asyncio.get_event_loop().time()
            })

            # Сохраняем
            with open(self.account_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            logger.info(f"💾 Данные бота сохранены: @{username}")

        except Exception as e:
            logger.error(f"❌ Ошибка сохранения данных бота: {e}")

    async def promote_account_to_admin(self, account, chat_link: str) -> bool:
        """Выдает аккаунту права администратора"""
        if not self.inviter_bot:
            logger.error("❌ InviterBot не инициализирован")
            return False

        return await self.inviter_bot.promote_user_to_admin(account, chat_link)

    async def revoke_admin_rights(self, account, chat_link: str) -> bool:
        """Отзывает права администратора у аккаунта"""
        if not self.inviter_bot:
            logger.error("❌ InviterBot не инициализирован")
            return False

        return await self.inviter_bot.revoke_admin_rights(account, chat_link)

    async def check_bot_permissions(self, chat_link: str) -> Dict[str, bool]:
        """Проверяет права бота в чате"""
        if not self.inviter_bot:
            logger.error("❌ InviterBot не инициализирован")
            return {}

        return await self.inviter_bot.test_bot_permissions(chat_link)

    async def send_test_message(self, chat_link: str) -> bool:
        """Отправляет тестовое сообщение в чат"""
        if not self.inviter_bot:
            logger.error("❌ InviterBot не инициализирован")
            return False

        return await self.inviter_bot.send_test_message(chat_link)

    async def close(self):
        """Закрывает все соединения"""
        try:
            if self.inviter_bot:
                await self.inviter_bot.close()

            if self.account and self.account.client:
                await self.account.client.disconnect()

            logger.debug(f"🔌 BotManager закрыт: {self.account_name}")

        except Exception as e:
            logger.error(f"❌ Ошибка закрытия BotManager: {e}")

    def __str__(self):
        return f"BotManager({self.account_name}, @{self.bot_username})"

    def __repr__(self):
        return self.__str__()