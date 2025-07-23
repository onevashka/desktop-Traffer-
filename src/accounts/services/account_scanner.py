# src/accounts/services/account_scanner.py
"""
Сервис сканирования аккаунтов - отвечает только за поиск и загрузку аккаунтов из папок
"""

import asyncio
from pathlib import Path
from typing import Dict, List
from loguru import logger

from src.entities.account import AccountData
from src.accounts.impl.account import Account


class AccountScanner:
    """Сканирует папки и создает объекты аккаунтов"""

    def __init__(self, traffic_folders: Dict[str, Path], sales_folders: Dict[str, Path]):
        self.traffic_folders = traffic_folders
        self.sales_folders = sales_folders
        logger.debug("🔍 AccountScanner инициализирован")

    async def scan_all_folders(self) -> Dict[str, Dict[str, AccountData]]:
        """
        Сканирует все папки и возвращает раздельные хранилища

        Returns:
            {
                'traffic': {account_name: AccountData, ...},
                'sales': {account_name: AccountData, ...}
            }
        """
        logger.info("🔍 AccountScanner: начинаем полное сканирование...")

        traffic_accounts = {}
        sales_accounts = {}

        # Сканируем трафик
        traffic_total = 0
        for status, folder_path in self.traffic_folders.items():
            accounts = await self._scan_folder(folder_path, "traffic", status)
            traffic_accounts.update(accounts)
            traffic_total += len(accounts)
            logger.debug(f"  📁 Трафик/{status}: {len(accounts)} аккаунтов")

        # Сканируем продажи
        sales_total = 0
        for status, folder_path in self.sales_folders.items():
            accounts = await self._scan_folder(folder_path, "sales", status)
            sales_accounts.update(accounts)
            sales_total += len(accounts)
            logger.debug(f"  💰 Продажи/{status}: {len(accounts)} аккаунтов")

        logger.info(
            f"✅ Сканирование завершено: трафик={traffic_total}, продажи={sales_total}, всего={traffic_total + sales_total}")

        return {
            'traffic': traffic_accounts,
            'sales': sales_accounts
        }

    async def scan_category(self, category: str) -> Dict[str, AccountData]:
        """
        Сканирует только одну категорию (трафик или продажи)

        Args:
            category: "traffic" или "sales"

        Returns:
            Dict[str, AccountData]: Аккаунты этой категории
        """
        logger.info(f"🔍 Сканируем категорию: {category}")

        if category == "traffic":
            folders = self.traffic_folders
        elif category == "sales":
            folders = self.sales_folders
        else:
            logger.error(f"❌ Неизвестная категория: {category}")
            return {}

        accounts = {}
        total_count = 0

        for status, folder_path in folders.items():
            folder_accounts = await self._scan_folder(folder_path, category, status)
            accounts.update(folder_accounts)
            total_count += len(folder_accounts)
            logger.debug(f"  📁 {category}/{status}: {len(folder_accounts)} аккаунтов")

        logger.info(f"✅ Категория {category} отсканирована: {total_count} аккаунтов")
        return accounts

    async def _scan_folder(self, folder_path: Path, category: str, status: str) -> Dict[str, AccountData]:
        """
        Сканирует одну папку

        Args:
            folder_path: Путь к папке
            category: Категория аккаунтов
            status: Статус (папка)

        Returns:
            Dict[str, AccountData]: Найденные аккаунты
        """
        if not folder_path.exists():
            logger.debug(f"⏭️  Папка не существует: {folder_path}")
            return {}

        logger.debug(f"🔍 Сканируем папку: {folder_path} (категория: {category}, статус: {status})")

        accounts = {}

        try:
            session_files = list(folder_path.glob("*.session"))
            logger.debug(f"📁 Найдено .session файлов: {len(session_files)}")

            for session_file in session_files:
                json_file = session_file.with_suffix(".json")

                if json_file.exists():
                    name = session_file.stem

                    # Проверяем дубликаты
                    if name in accounts:
                        logger.warning(f"⚠️  Дубликат в {category}/{status}: {name}")
                        continue

                    try:
                        # Создаем объект Account
                        account = Account(session_file, json_file)

                        # Получаем информацию из аккаунта
                        info = await account.get_info()

                        # Создаем полные данные аккаунта
                        account_data = AccountData(
                            name=name,
                            category=category,
                            status=status,
                            account=account,
                            info=info
                        )

                        accounts[name] = account_data

                        logger.debug(
                            f"  ✅ Загружен в {category}: {name} | {info.get('full_name', '?')} | {info.get('phone', '?')}")

                    except Exception as e:
                        logger.error(f"❌ Ошибка создания Account для {name}: {e}")
                        continue
                else:
                    logger.debug(f"⚠️  JSON файл не найден для: {session_file.name}")

        except Exception as e:
            logger.error(f"❌ Ошибка сканирования {folder_path}: {e}")

        logger.debug(f"📊 Папка {folder_path.name}: загружено {len(accounts)} аккаунтов")
        return accounts

    def get_folder_info(self, category: str) -> Dict[str, Dict]:
        """
        Получает информацию о папках категории

        Returns:
            Dict: Информация о папках (путь, существование, etc.)
        """
        if category == "traffic":
            folders = self.traffic_folders
        elif category == "sales":
            folders = self.sales_folders
        else:
            return {}

        folder_info = {}
        for status, folder_path in folders.items():
            folder_info[status] = {
                'path': str(folder_path),
                'exists': folder_path.exists(),
                'session_files': len(list(folder_path.glob("*.session"))) if folder_path.exists() else 0,
                'json_files': len(list(folder_path.glob("*.json"))) if folder_path.exists() else 0
            }

        return folder_info