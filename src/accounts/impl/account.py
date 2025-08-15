# TeleCRM/core/account.py
import asyncio

import phonenumbers
import datetime
from datetime import timezone
from pathlib import Path
from telethon import TelegramClient
from telethon.errors import (
    SessionRevokedError, AuthKeyUnregisteredError,
    UserDeactivatedBanError, UserDeactivatedError
)
from loguru import logger

from src.accounts.impl.utils import load_json_data, save_json_data
from src.entities import ProxyTelethon
from telethon import functions


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
        # Получаем прокси для э того аккаунта
        from src.proxies.manager import get_proxy_for_account
        proxy = get_proxy_for_account(self.name)

        if proxy:
            logger.debug(f"🌐 Используем прокси для {self.name}: {proxy['addr']}:{proxy['port']}")
        else:
            logger.warning(f"⚠️ Прокси не найден для {self.name}, подключаемся напрямую")


        # Создаём клиента с прокси
        self.client = TelegramClient(
            session=str(self.session_path),
            api_id=int(cfg.get('app_id')),
            api_hash=cfg.get('app_hash'),
            proxy=(proxy.get('proxy_type'), proxy.get('addr'), proxy.get('port'), proxy.get('rdns'), proxy.get('username'), proxy.get('password')),  # Может быть None или словарь
            lang_code=cfg.get('lang_code', 'en'),
            device_model=cfg.get('device'),
            app_version=cfg.get('app_version'),
            system_version=cfg.get('sdk'),
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

        except Exception as e:
            logger.error(f"[{self.name}] Ошибка при подклчюении аккаунта {e}")
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

    async def join(self, link: str):
        """
        Присоединяется к чату/каналу по ссылке

        Args:
            link: Ссылка на чат/канал

        Returns:
            chat_entity - информация о чате, или код ошибки
        """
        from telethon.tl.functions.messages import ImportChatInviteRequest
        from telethon.tl.functions.channels import JoinChannelRequest
        from telethon.errors import UserAlreadyParticipantError

        try:
            result = await self.client(functions.help.GetAppConfigRequest(hash=0))
            frozen, details = self.is_frozen(result)
            if frozen:
                return "FROZEN_ACCOUNT"

            if not self.client or not await self.client.is_user_authorized():
                logger.error(f"[{self.name}] Клиент не подключен или не авторизован")
                return "NOT_CONNECTED"

            entity = await self.client.get_entity(link)

            # Приватный чат/канал
            if link.startswith("https://t.me/+"):
                invite_hash = link.split("+")[1]
                result = await self.client(ImportChatInviteRequest(invite_hash))
                logger.info(f"[{self.name}] Вступил в приватный чат {link}")

                # Получаем информацию о чате
                if hasattr(result, 'chats') and result.chats:
                    chat_entity = result.chats[0]
                    return "SUCCESS"
                return "SUCCESS"

            # Публичный чат/канал
            else:
                # Извлекаем username из ссылки
                if link.startswith("https://t.me/"):
                    username = link.split("/")[-1]
                elif link.startswith("@"):
                    username = link[1:]
                else:
                    username = link

                result = await self.client(JoinChannelRequest(username))

                # Получаем entity чата
                try:
                    chat_entity = await self.client.get_entity(username)
                    return "SUCCESS"
                except:
                    return "SUCCESS"

        except UserAlreadyParticipantError:
            logger.warning(f"[{self.name}] Уже участник чата {link}")

            # Пытаемся получить entity чата даже если уже участник
            try:
                if link.startswith("https://t.me/+"):
                    # Для приватных чатов сложнее, но попробуем
                    return "ALREADY_PARTICIPANT"
                else:
                    # Для публичных можем получить entity
                    username = link.split("/")[-1] if "/" in link else link
                    username = username[1:] if username.startswith("@") else username
                    chat_entity = await self.client.get_entity(username)
                    return chat_entity
            except:
                return "ALREADY_PARTICIPANT"

        except Exception as e:
            error_text = str(e)

            # Анализируем различные типы ошибок
            if "FROZEN_METHOD_INVALID" in error_text:
                return "FROZEN_ACCOUNT"

            elif "Nobody is using this username" in error_text or "username is unacceptable" in error_text:
                logger.error(f"[{self.name}] Чат не существует или неверная ссылка: {link}")
                return "CHAT_NOT_FOUND"

            elif "No user has" in error_text:
                logger.warning(f"[{self.name}] Данный чат не найден {link} {e}")
                return "USER_NOT_FOUND"

            elif "successfully requested to join" in error_text:
                logger.warning(f"[{self.name}] Отправлен запрос на вступление в {link}")
                return "REQUEST_SENT"

            elif "deleted/deactivated" in error_text:
                logger.error(f"[{self.name}] Аккаунт удален или заблокирован")
                return "ACCOUNT_DEACTIVATED"

            elif "key is not registered" in error_text:
                logger.error(f"[{self.name}] Неверный invite hash для {link}")
                return "INVALID_INVITE"

            elif "flood" in error_text.lower():
                logger.error(f"[{self.name}] Флуд при попытке вступить в {link}")
                return "FLOOD_WAIT"

            elif "The channel specified is private and you lack permission to access it. Another reason may be that you were banned from it" in error_text:
                logger.error(f"[{self.name}] Аккаунт ранее был кикнут из группы {link}")
                return f"ERROR: {error_text[:100]}"

            else:
                logger.error(f"[{self.name}] Ошибка при вступлении в {link}: {e}")
                return f"ERROR: {error_text[:100]}"

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
            pass

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

    def is_frozen(self, app_config) -> tuple:
        if not app_config or not hasattr(app_config, 'config') or not hasattr(app_config.config, 'value'):
            return False, None

        values = {v.key: v.value for v in app_config.config.value}

        since = values.get("freeze_since_date")
        until = values.get("freeze_until_date")
        appeal = values.get("freeze_appeal_url")

        def to_datetime(val):
            try:
                return datetime.fromtimestamp(val.value, tz=timezone.utc)
            except Exception:
                return None

        if since or until or appeal:
            result = {
                "since": to_datetime(since) if since else None,
                "until": to_datetime(until) if until else None,
                "appeal_url": appeal.value if hasattr(appeal, 'value') else str(appeal)
            }
            return True, result

        return False, None

