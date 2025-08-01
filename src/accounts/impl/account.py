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

        self._sync_session_name()

        self.name = self.account_data.get("session")

        self.client = None

    async def create_client(self):
        """
        Ленивое создание и конфигурация TelegramClient.
        """
        if self.client:
            return

        cfg = self.account_data

        # Получаем прокси для этого аккаунта
        from src.proxies.manager import get_proxy_for_account
        proxy = get_proxy_for_account(self.name)

        if proxy:
            logger.debug(f"🌐 Используем прокси для {self.name}: {proxy['addr']}:{proxy['port']}")
        else:
            logger.warning(f"⚠️ Прокси не найден для {self.name}, подключаемся напрямую")

        # Создаём клиента с прокси
        self.client = TelegramClient(
            session=str(self.session_path),
            api_id=cfg.get('api_id'),
            api_hash=cfg.get('api_hash'),
            proxy=(proxy.get('proxy_type'), proxy.get('host'), proxy.get('port'), proxy.get('rdns'), proxy.get('login'), proxy.get('password')),  # Может быть None или словарь
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


    async def disconnect(self) -> bool:
        """
        Останавливает клиент.
        """
        try:
            await self.client.disconnect()
            return True
        except Exception as e:
            logger.error(f"Ошибка при отключении аккаунта: {e}")
            return False

    def _sync_session_name(self):
        """
        Проверяет и синхронизирует переменную 'session' в JSON с именем файла.
        """
        actual_name = self.session_path.stem  # Чистое имя файла без расширения
        json_session_name = self.account_data.get('session', '')

        # Проверяем: есть ли переменная session в JSON
        if 'session' not in self.account_data:
            # Нет переменной - создаем с актуальным именем
            logger.debug(f"➕ [{actual_name}] Добавляем переменную 'session': '{actual_name}'")
            # НЕ ОБНОВЛЯЕМ self.account_data здесь - только через update_json
            self.update_json(session=actual_name)

        elif json_session_name != actual_name:
            # Есть переменная, но имя не совпадает - обновляем
            logger.debug(f"🔄 [{actual_name}] Обновляем 'session': '{json_session_name}' -> '{actual_name}'")
            # НЕ ОБНОВЛЯЕМ self.account_data здесь - только через update_json
            self.update_json(session=actual_name)

        else:
            # Все в порядке - имена совпадают
            logger.debug(f"✅ [{actual_name}] Имя session актуально: '{actual_name}'")

    async def get_info(self) -> dict:
        """
        Возвращает словарь с информацией об аккаунте.
        Использует актуальное имя session из JSON.
        """
        first = self.account_data.get('first_name', '') or ''
        last = self.account_data.get('last_name', '') or ''
        full_name = (first + ' ' + last).strip()

        # Берем имя session из JSON (уже синхронизированное)
        session_name = self.account_data.get('session', self.name)

        raw_phone = (self.account_data.get('phone', '') or '').strip()

        parse_phone = raw_phone
        if parse_phone and not parse_phone.startswith('+'):
            parse_phone = '+' + parse_phone

        geo = ''
        if parse_phone:
            try:
                import phonenumbers
                pn = phonenumbers.parse(parse_phone, None)
                geo = phonenumbers.region_code_for_number(pn) or ''
            except Exception:
                geo = ''

        return {
            'full_name': full_name,
            'session_name': session_name,  # Актуальное имя из JSON
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
