# TeleCRM/core/telegram_client.py

from pathlib import Path
from telethon import TelegramClient
from telethon.errors import SessionRevokedError, AuthKeyUnregisteredError, UserDeactivatedBanError, UserDeactivatedError
from.utils import load_json_data
from loguru import logger

class Account:
    """
    Обёртка над Telethon TelegramClient для одного аккаунта.
    При создании указываем пути к .session и API-данные.
    """
    def __init__(self, session_path: Path, json_path: Path, proxy: Proxy):
        """
        session_path — полный путь к файлу session
        json_path — полный путь к файлу json
        """
        self.session_path = session_path
        self.json_path = json_path
        self.account_data = load_json_data(self.json_path)
        self.proxy = proxy

        self.client = TelegramClient(
            session=self.session_path,
            api_hash=self.account_data.get('api_hash'),
            api_id=self.account_data.get('api_id'),
            lang_code=self.account_data.get('lang_code', 'en'),
            device_model=self.account_data.get('device_model'),
            app_version=self.account_data.get('app_version'),
            system_version=self.account_data.get('system_version'),
            system_lang_code=self.account_data.get('system_lang_code', 'en-US'),
        )
        self.client._init_request.lang_pack = self.account_data.get('lang_pack')


    async def connect(self):
        """
        Коннектит клиент.
        Вызывается в асинхронном контексте.
        """
        try:
            await self.client.connect()
            if await self.client.is_user_authorized():
                return True
            else:
                return False
        except (SessionRevokedError, AuthKeyUnregisteredError,) as e:
            logger.error(
                f"[{account.phone}] Cессия (ключ авторизации) была аннулирована со стороны Telegram или владельцем аккаунта.")
            return False

        except (UserDeactivatedBanError, UserDeactivatedError) as e:
            logger.error(f"[{account.phone}] Аккаунт деактивирован")
            return False




    async def stop(self):
        """
        Останавливает клиент.
        """
        await self.client.disconnect()
