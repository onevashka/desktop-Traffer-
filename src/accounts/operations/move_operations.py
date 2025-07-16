"""
Операции перемещения аккаунтов
"""

from typing import List, Dict, Tuple
from pathlib import Path
from loguru import logger
import shutil


class AccountMover:
    """Класс для операций перемещения аккаунтов"""

    def __init__(self, account_manager):
        self.manager = account_manager

    def get_available_destinations(self, current_category: str, current_status: str) -> List[Dict]:
        """
        Получает список доступных папок для перемещения.

        Returns:
            Список словарей с информацией о доступных папках
        """
        destinations = []

        # Добавляем папки трафика
        for status, folder_path in self.manager.traffic_folders.items():
            if not (current_category == "traffic" and current_status == status):
                destinations.append({
                    'category': 'traffic',
                    'status': status,
                    'display_name': f"🚀 Трафик → {self._get_status_display(status)}",
                    'folder_path': folder_path
                })

        # Добавляем папки продаж
        for status, folder_path in self.manager.sales_folders.items():
            if not (current_category == "sales" and current_status == status):
                destinations.append({
                    'category': 'sales',
                    'status': status,
                    'display_name': f"💰 Продажи → {self._get_status_display(status)}",
                    'folder_path': folder_path
                })

        return destinations

    def move_accounts(self, account_names: List[str], source_category: str,
                      target_category: str, target_status: str) -> Dict[str, bool]:
        """
        Перемещает аккаунты между папками.

        Returns:
            Словарь {имя_аккаунта: успех_перемещения}
        """
        source_storage = self._get_accounts_storage(source_category)
        target_storage = self._get_accounts_storage(target_category)
        target_folder = self._get_folder_path(target_category, target_status)

        if not all([source_storage, target_storage, target_folder]):
            return {name: False for name in account_names}

        results = {}

        for account_name in account_names:
            try:
                success = self._move_single_account(
                    account_name, source_storage, target_storage,
                    target_folder, target_category, target_status
                )
                results[account_name] = success
            except Exception as e:
                logger.error(f"❌ Ошибка перемещения {account_name}: {e}")
                results[account_name] = False

        return results

    def _move_single_account(self, account_name: str, source_storage: dict,
                             target_storage: dict, target_folder: Path,
                             target_category: str, target_status: str) -> bool:
        """Перемещает один аккаунт"""
        if account_name not in source_storage:
            logger.warning(f"⚠️  Аккаунт {account_name} не найден в источнике")
            return False

        account_data = source_storage[account_name]
        account = account_data.account

        # Пути исходных файлов
        old_session = account.session_path
        old_json = account.json_path

        # Пути новых файлов
        new_session = target_folder / old_session.name
        new_json = target_folder / old_json.name

        logger.info(f"📦 Перемещаем {account_name}: {old_session.parent.name} → {target_folder.name}")

        # Создаем целевую папку если не существует
        target_folder.mkdir(parents=True, exist_ok=True)

        # Перемещаем файлы
        shutil.move(str(old_session), str(new_session))
        shutil.move(str(old_json), str(new_json))

        # Обновляем пути в объекте Account
        account.session_path = new_session
        account.json_path = new_json

        # Обновляем статус и категорию
        account_data.category = target_category
        account_data.status = target_status

        # Перемещаем между хранилищами
        del source_storage[account_name]
        target_storage[account_name] = account_data

        logger.info(f"✅ Аккаунт {account_name} перемещен")
        return True

    def _get_accounts_storage(self, category: str):
        """Получает хранилище аккаунтов"""
        if category == "traffic":
            return self.manager.traffic_accounts
        elif category == "sales":
            return self.manager.sales_accounts
        return None

    def _get_folder_path(self, category: str, status: str) -> Path:
        """Получает путь к папке"""
        if category == "traffic":
            return self.manager.traffic_folders.get(status)
        elif category == "sales":
            return self.manager.sales_folders.get(status)
        return None

    def _get_status_display(self, status: str) -> str:
        """Получает отображаемое имя статуса"""
        status_names = {
            "active": "Активные",
            "dead": "Мертвые",
            "frozen": "Замороженные",
            "invalid": "Неверный формат",
            "registration": "Регистрация",
            "ready_tdata": "TData готовые",
            "ready_sessions": "Session готовые",
            "middle": "Средние"
        }
        return status_names.get(status, status)