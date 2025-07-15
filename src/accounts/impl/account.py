# TeleCRM/core/account.py
import phonenumbers

from pathlib import Path
from telethon import TelegramClient
from telethon.errors import (
    SessionRevokedError, AuthKeyUnregisteredError,
    UserDeactivatedBanError, UserDeactivatedError
)
from loguru import logger

from src.accounts.impl.utils import load_json_data, save_json_data
from src.entities import ProxyTelethon


class Account:
    """
    Обёртка над Telethon TelegramClient для одного аккаунта.
    При создании указываем пути к .session и API-данные.
    """
    def __init__(self, session_path: Path, json_path: Path):
        """
        session_path — полный путь к файлу session
        json_path — полный путь к файлу json
        """
        self.session_path = session_path
        self.json_path = json_path
        self.account_data: dict = load_json_data(self.json_path)
        self.proxy: ProxyTelethon | None = None
        self.name = session_path.stem

        self.client = None

    async def create_client(self):
        """
        Ленивое создание и конфигурация TelegramClient.
        Вызывать только после установки proxy, если он нужен.
        """
        if self.client:
            return
        cfg = self.account_data
        # Создаём клиента, proxy по умолчанию может быть None
        self.client = TelegramClient(
            session=str(self.session_path),
            api_id=cfg.get('api_id'),
            api_hash=cfg.get('api_hash'),
            proxy=self.proxy,
            lang_code=cfg.get('lang_code', 'en'),
            device_model=cfg.get('device_model'),
            app_version=cfg.get('app_version'),
            system_version=cfg.get('system_version'),
            system_lang_code=cfg.get('system_lang_code', 'en-US'),
        )
        if lp := cfg.get('lang_pack'):
            self.client._init_request.lang_pack = lp


    async def connect(self) -> bool:
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
                f"[{self.name}] Cессия (ключ авторизации) была аннулирована со стороны Telegram или владельцем аккаунта.")
            return False

        except (UserDeactivatedBanError, UserDeactivatedError) as e:
            logger.error(f"[{self.name}] Аккаунт деактивирован")
            return False


    async def stop(self) -> bool:
        """
        Останавливает клиент.
        """
        try:
            await self.client.disconnect()
            return True
        except Exception as e:
            logger.error(f"Ошибка при отключении аккаунта: {e}")
            return False

    async def get_info(self) -> dict:
        """
        Возвращает словарь со следующими полями:
          - full_name: first_name + last_name
          - session_name: имя файла .session (из JSON или по session_path)
          - phone: ровно из JSON (без добавления '+')
          - geo: двухбуквенный ISO‑код страны по телефону
        """
        first = self.account_data.get('first_name', '') or ''
        last = self.account_data.get('last_name', '') or ''
        full_name = (first + ' ' + last).strip()

        sess_field = self.account_data.get('session', '')
        session_name = Path(sess_field).stem if sess_field else self.session_path.stem

        raw_phone = (self.account_data.get('phone', '') or '').strip()

        parse_phone = raw_phone
        if parse_phone and not parse_phone.startswith('+'):
            parse_phone = '+' + parse_phone

        geo = ''
        if parse_phone:
            try:
                pn = phonenumbers.parse(parse_phone, None)
                geo = phonenumbers.region_code_for_number(pn) or ''
            except Exception:
                geo = ''

        return {
            'full_name': full_name,
            'session_name': session_name,
            'phone': raw_phone,
            'geo': geo
        }

    def update_json(self, **fields) -> None:
        """
        Обновляет ключи в self.account_data и сразу сохраняет JSON-файл.
        Пример: self.update_json(session='12345', role='admin')
        """
        # Обновляем только изменившиеся или новые значения
        changed = False
        for k, v in fields.items():
            if self.account_data.get(k) != v:
                self.account_data[k] = v
                changed = True

        if changed:
            save_json_data(self.json_path, self.account_data)
