"""
Операции удаления аккаунтов
"""

from typing import List, Dict
from pathlib import Path
from loguru import logger


class AccountDeleter:
    """Класс для операций удаления аккаунтов"""

    def __init__(self, account_manager):
        """
        account_manager: Ссылка на AccountManager для доступа к хранилищам
        """
        self.manager = account_manager

    def delete_accounts(self, account_names: List[str], category: str) -> Dict[str, bool]:
        """
        Удаляет аккаунты из файловой системы и менеджера.

        Args:
            account_names: Список имен аккаунтов для удаления
            category: Категория аккаунтов ("traffic" или "sales")

        Returns:
            Словарь {имя_аккаунта: успех_удаления}
        """
        # Получаем правильное хранилище
        accounts_storage = self._get_accounts_storage(category)
        if not accounts_storage:
            return {name: False for name in account_names}

        results = {}

        for account_name in account_names:
            try:
                success = self._delete_single_account(account_name, accounts_storage, category)
                results[account_name] = success
            except Exception as e:
                logger.error(f"❌ Ошибка удаления {account_name}: {e}")
                results[account_name] = False

        return results

    def get_deletion_info(self, account_names: List[str], category: str) -> List[Dict]:
        """
        Получает информацию об аккаунтах для подтверждения удаления.

        Returns:
            Список словарей с информацией об аккаунтах
        """
        accounts_storage = self._get_accounts_storage(category)
        if not accounts_storage:
            return []

        accounts_info = []

        for account_name in account_names:
            if account_name in accounts_storage:
                account_data = accounts_storage[account_name]
                info = account_data.info

                accounts_info.append({
                    'name': account_name,
                    'full_name': info.get('full_name', '?'),
                    'phone': info.get('phone', '?'),
                    'status': account_data.status,
                    'category': category,
                    'session_file': str(account_data.account.session_path),
                    'json_file': str(account_data.account.json_path)
                })

        return accounts_info

    def _get_accounts_storage(self, category: str):
        """Получает правильное хранилище аккаунтов"""
        if category == "traffic":
            return self.manager.traffic_accounts
        elif category == "sales":
            return self.manager.sales_accounts
        else:
            logger.error(f"❌ Неизвестная категория: {category}")
            return None

    def _delete_single_account(self, account_name: str, accounts_storage: dict, category: str) -> bool:
        """Удаляет один аккаунт"""
        # Проверяем что аккаунт существует
        if account_name not in accounts_storage:
            logger.warning(f"⚠️  Аккаунт {account_name} не найден в {category}")
            return False

        account_data = accounts_storage[account_name]
        account = account_data.account

        # Получаем пути к файлам
        session_file = account.session_path
        json_file = account.json_path

        logger.info(f"🗑️  Удаляем аккаунт {account_name} из {category}")
        logger.debug(f"   Session: {session_file}")
        logger.debug(f"   JSON: {json_file}")

        # Удаляем файлы
        files_deleted = 0
        if session_file.exists():
            session_file.unlink()
            files_deleted += 1
            logger.debug(f"   ✅ Session файл удален")

        if json_file.exists():
            json_file.unlink()
            files_deleted += 1
            logger.debug(f"   ✅ JSON файл удален")

        # Удаляем из хранилища
        del accounts_storage[account_name]

        logger.info(f"✅ Аккаунт {account_name} удален ({files_deleted} файлов)")
        return True