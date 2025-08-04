# src/modules/impl/inviter/bot_account_manager.py
"""
Менеджер аккаунтов-держателей ботов для инвайта через админку
"""

import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from loguru import logger

from paths import WORK_ACCOUNTS_TRAFFER_FOLDER, BOT_HOLDERS_FOLDER


class BotAccountManager:
    """Управляет аккаунтами для ботов"""

    def __init__(self):
        # Убеждаемся что папка существует
        BOT_HOLDERS_FOLDER.mkdir(parents=True, exist_ok=True)
        logger.debug("🤖 BotAccountManager инициализирован")

    def assign_bot_account(self, account_name: str) -> Tuple[bool, str]:
        """
        Назначает аккаунт держателем бота (перемещает в специальную папку)

        Args:
            account_name: Имя аккаунта

        Returns:
            Tuple[успех, сообщение]
        """
        try:
            # Пути к файлам
            source_session = WORK_ACCOUNTS_TRAFFER_FOLDER / f"{account_name}.session"
            source_json = WORK_ACCOUNTS_TRAFFER_FOLDER / f"{account_name}.json"

            dest_session = BOT_HOLDERS_FOLDER / f"{account_name}.session"
            dest_json = BOT_HOLDERS_FOLDER / f"{account_name}.json"

            # Проверяем существование исходных файлов
            if not source_session.exists() or not source_json.exists():
                return False, f"Файлы аккаунта {account_name} не найдены"

            # Проверяем что аккаунт еще не держатель бота
            if dest_session.exists():
                return False, f"Аккаунт {account_name} уже является держателем бота"

            # Перемещаем файлы
            logger.info(f"🤖 Назначаем {account_name} держателем бота...")

            shutil.move(str(source_session), str(dest_session))
            shutil.move(str(source_json), str(dest_json))

            logger.info(f"✅ Аккаунт {account_name} перемещен в держатели ботов")

            # Обновляем AccountManager
            self._update_account_manager(account_name, 'assign')

            return True, f"Аккаунт {account_name} назначен держателем бота"

        except Exception as e:
            logger.error(f"❌ Ошибка назначения бота для {account_name}: {e}")
            return False, f"Ошибка: {str(e)}"

    def release_bot_account(self, account_name: str) -> Tuple[bool, str]:
        """
        Освобождает аккаунт от бота (возвращает в основную папку)

        Args:
            account_name: Имя аккаунта

        Returns:
            Tuple[успех, сообщение]
        """
        try:
            # Пути к файлам
            source_session = BOT_HOLDERS_FOLDER / f"{account_name}.session"
            source_json = BOT_HOLDERS_FOLDER / f"{account_name}.json"

            dest_session = WORK_ACCOUNTS_TRAFFER_FOLDER / f"{account_name}.session"
            dest_json = WORK_ACCOUNTS_TRAFFER_FOLDER / f"{account_name}.json"

            # Проверяем существование исходных файлов
            if not source_session.exists() or not source_json.exists():
                return False, f"Аккаунт {account_name} не является держателем бота"

            # Перемещаем файлы обратно
            logger.info(f"🔄 Освобождаем {account_name} от бота...")

            shutil.move(str(source_session), str(dest_session))
            shutil.move(str(source_json), str(dest_json))

            logger.info(f"✅ Аккаунт {account_name} возвращен в основную папку")

            # Обновляем AccountManager
            self._update_account_manager(account_name, 'release')

            return True, f"Аккаунт {account_name} освобожден от бота"

        except Exception as e:
            logger.error(f"❌ Ошибка освобождения бота для {account_name}: {e}")
            return False, f"Ошибка: {str(e)}"

    def get_bot_holders(self) -> List[Dict]:
        """
        Получает список всех держателей ботов

        Returns:
            List[Dict]: Список информации об аккаунтах
        """
        holders = []

        try:
            for session_file in BOT_HOLDERS_FOLDER.glob("*.session"):
                json_file = session_file.with_suffix(".json")

                if json_file.exists():
                    import json
                    try:
                        with open(json_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)

                        holders.append({
                            'name': session_file.stem,
                            'phone': data.get('phone', ''),
                            'full_name': f"{data.get('first_name', '')} {data.get('last_name', '')}".strip(),
                            'session_path': str(session_file),
                            'json_path': str(json_file)
                        })
                    except Exception as e:
                        logger.error(f"❌ Ошибка чтения {json_file}: {e}")

        except Exception as e:
            logger.error(f"❌ Ошибка получения держателей ботов: {e}")

        return holders

    def is_bot_holder(self, account_name: str) -> bool:
        """
        Проверяет является ли аккаунт держателем бота

        Args:
            account_name: Имя аккаунта

        Returns:
            bool: True если держатель бота
        """
        session_file = BOT_HOLDERS_FOLDER / f"{account_name}.session"
        return session_file.exists()

    def get_bot_holder_info(self, account_name: str) -> Optional[Dict]:
        """
        Получает информацию о держателе бота

        Args:
            account_name: Имя аккаунта

        Returns:
            Dict или None
        """
        session_file = BOT_HOLDERS_FOLDER / f"{account_name}.session"
        json_file = BOT_HOLDERS_FOLDER / f"{account_name}.json"

        if not session_file.exists() or not json_file.exists():
            return None

        try:
            import json
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            return {
                'name': account_name,
                'phone': data.get('phone', ''),
                'full_name': f"{data.get('first_name', '')} {data.get('last_name', '')}".strip(),
                'session_path': str(session_file),
                'json_path': str(json_file),
                'app_id': data.get('app_id'),
                'app_hash': data.get('app_hash')
            }
        except Exception as e:
            logger.error(f"❌ Ошибка получения информации о {account_name}: {e}")
            return None

    def _update_account_manager(self, account_name: str, action: str):
        """Обновляет AccountManager после изменений"""
        try:
            from src.accounts.manager import _account_manager

            if _account_manager:
                # Запускаем обновление категории трафика
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(_account_manager.refresh_category("traffic"))
                loop.close()

                logger.info(f"📊 AccountManager обновлен после {action} для {account_name}")
        except Exception as e:
            logger.error(f"❌ Ошибка обновления AccountManager: {e}")


# Глобальный экземпляр
_bot_account_manager: Optional[BotAccountManager] = None


def get_bot_account_manager() -> BotAccountManager:
    """Получает глобальный экземпляр менеджера ботов"""
    global _bot_account_manager
    if _bot_account_manager is None:
        _bot_account_manager = BotAccountManager()
    return _bot_account_manager


# Удобные функции
def assign_bot_account(account_name: str) -> Tuple[bool, str]:
    """Назначает аккаунт держателем бота"""
    manager = get_bot_account_manager()
    return manager.assign_bot_account(account_name)


def release_bot_account(account_name: str) -> Tuple[bool, str]:
    """Освобождает аккаунт от бота"""
    manager = get_bot_account_manager()
    return manager.release_bot_account(account_name)


def get_bot_holders() -> List[Dict]:
    """Получает список держателей ботов"""
    manager = get_bot_account_manager()
    return manager.get_bot_holders()


def is_bot_holder(account_name: str) -> bool:
    """Проверяет является ли аккаунт держателем бота"""
    manager = get_bot_account_manager()
    return manager.is_bot_holder(account_name)