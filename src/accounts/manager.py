# src/accounts/manager.py
"""
Центральный AccountManager - создает объекты Account сразу при сканировании
"""

import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from loguru import logger

from src.accounts.impl.account import Account
from paths import *


@dataclass
class AccountData:
    """Полная информация об аккаунте"""
    name: str  # имя аккаунта (без расширения)
    category: str  # "traffic" или "sales"
    status: str  # папка где лежит: "active", "dead", "frozen", etc.
    account: Account  # объект аккаунта с данными
    info: dict  # кешированная информация из account.get_info()


class AccountManager:
    """
    Центральный менеджер аккаунтов.
    Создает объекты Account сразу при сканировании и готовит всю информацию.
    """

    def __init__(self):
        # Маппинг папок трафика
        self.traffic_folders = {
            "active": WORK_ACCOUNTS_TRAFFER_FOLDER,
            "dead": DEAD_TRAFFER_FOLDER,
            "frozen": FROZEN_TRAFFER_FOLDER,
            "invalid": INVALID_TRAFFER_FORMAT_FOLDER
        }

        # Маппинг папок продаж
        self.sales_folders = {
            "registration": WORK_ACCOUNTS_SALE_FOLDER,
            "ready_tdata": TDATA_FOLDER,
            "ready_sessions": SESSIONS_JSON_FOLDER,
            "middle": MIDDLE_ACCOUNTS_FOLDER,
            "dead": DEAD_SALES_FOLDER,
            "frozen": FROZEN_SALES_FOLDER,
            "invalid": INVALID_SALES_FORMAT_FOLDER
        }

        # Основное хранилище аккаунтов - все готовые к использованию
        self.accounts: Dict[str, AccountData] = {}

        logger.info("📋 AccountManager создан")

    async def scan_all_folders(self) -> None:
        """
        Сканирует все папки и создает объекты Account сразу.
        Подготавливает всю информацию для быстрого доступа.
        """
        logger.info("🔍 Начинаем полное сканирование и загрузку аккаунтов...")

        self.accounts.clear()

        # Сканируем папки трафика
        traffic_total = 0
        for status, folder_path in self.traffic_folders.items():
            count = await self._scan_folder(folder_path, "traffic", status)
            traffic_total += count
            logger.debug(f"  📁 Трафик/{status}: {count} аккаунтов")

        # Сканируем папки продаж
        sales_total = 0
        for status, folder_path in self.sales_folders.items():
            count = await self._scan_folder(folder_path, "sales", status)
            sales_total += count
            logger.debug(f"  💰 Продажи/{status}: {count} аккаунтов")

        total = len(self.accounts)
        logger.info(f"✅ Полная загрузка завершена! Трафик: {traffic_total}, Продажи: {sales_total}, Всего: {total}")

    async def _scan_folder(self, folder_path: Path, category: str, status: str) -> int:
        """Сканирует папку и создает объекты Account"""
        if not folder_path.exists():
            logger.debug(f"⏭️  Папка не существует: {folder_path}")
            return 0

        count = 0
        try:
            # Ищем .session файлы
            for session_file in folder_path.glob("*.session"):
                json_file = session_file.with_suffix(".json")

                # Проверяем наличие JSON
                if json_file.exists():
                    name = session_file.stem

                    # Избегаем дубликатов
                    if name in self.accounts:
                        logger.warning(f"⚠️  Дубликат аккаунта: {name}")
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

                        self.accounts[name] = account_data
                        count += 1

                        logger.debug(f"  ✅ Загружен: {name} | {info.get('full_name', '?')} | {info.get('phone', '?')}")

                    except Exception as e:
                        logger.error(f"❌ Ошибка создания Account для {name}: {e}")
                        continue

        except Exception as e:
            logger.error(f"❌ Ошибка сканирования {folder_path}: {e}")

        return count

    def get_folder_counts(self) -> Dict[str, Dict[str, int]]:
        """
        Возвращает количество аккаунтов в каждой папке.

        Returns:
            {
                "traffic": {"active": 10, "dead": 5, "frozen": 2, "invalid": 1},
                "sales": {"registration": 8, "ready_tdata": 15, ...}
            }
        """
        counts = {
            "traffic": {status: 0 for status in self.traffic_folders.keys()},
            "sales": {status: 0 for status in self.sales_folders.keys()}
        }

        # Считаем по аккаунтам
        for account_data in self.accounts.values():
            if account_data.category in counts and account_data.status in counts[account_data.category]:
                counts[account_data.category][account_data.status] += 1

        return counts

    def get_traffic_stats(self) -> List[Tuple[str, str, str]]:
        """Возвращает статистику для GUI трафика"""
        counts = self.get_folder_counts()["traffic"]

        return [
            ("Активных аккаунтов", str(counts["active"]), "#10B981"),
            ("Мертвых", str(counts["dead"]), "#EF4444"),
            ("Замороженных", str(counts["frozen"]), "#F59E0B"),
            ("Неверный формат", str(counts["invalid"]), "#6B7280")
        ]

    def get_sales_stats(self) -> List[Tuple[str, str, str]]:
        """Возвращает статистику для GUI продаж"""
        counts = self.get_folder_counts()["sales"]

        # Общий счетчик готовых к продаже
        ready_total = counts["ready_tdata"] + counts["ready_sessions"]

        return [
            ("Регистрация", str(counts["registration"]), "#3B82F6"),
            ("Готовых к продаже", str(ready_total), "#10B981"),
            ("Средних", str(counts["middle"]), "#8B5CF6"),
            ("Замороженных", str(counts["frozen"]), "#F59E0B"),
            ("Мертвых", str(counts["dead"]), "#EF4444")
        ]

    def get_accounts_by_category(self, category: str) -> List[str]:
        """Возвращает список имен аккаунтов по категории"""
        return [
            name for name, account_data in self.accounts.items()
            if account_data.category == category
        ]

    def get_accounts_by_status(self, category: str, status: str) -> List[str]:
        """Возвращает список аккаунтов по категории и статусу"""
        return [
            name for name, account_data in self.accounts.items()
            if account_data.category == category and account_data.status == status
        ]

    def get_account(self, name: str) -> Optional[Account]:
        """Возвращает объект Account по имени"""
        account_data = self.accounts.get(name)
        return account_data.account if account_data else None

    def get_account_info(self, name: str) -> Optional[dict]:
        """Возвращает кешированную информацию об аккаунте"""
        account_data = self.accounts.get(name)
        return account_data.info if account_data else None

    def get_table_data(self, category: str, limit: int = 50) -> List[List[str]]:
        """
        Возвращает данные для отображения в таблице.
        Использует уже загруженную информацию из аккаунтов.
        """
        # Получаем аккаунты нужной категории
        category_accounts = [
            account_data for account_data in self.accounts.values()
            if account_data.category == category
        ]

        # Ограничиваем количество
        category_accounts = category_accounts[:limit]

        table_data = []
        for i, account_data in enumerate(category_accounts, 1):
            info = account_data.info

            # Формируем строку таблицы с реальными данными
            row = [
                str(i),  # Номер
                f"@{info.get('session_name', account_data.name)}",  # Username
                info.get('geo', '?'),  # Гео из номера телефона
                "?",  # Дней создан (пока заглушка)
                "?",  # Последний онлайн (пока заглушка)
                info.get('full_name', '?') or '?',  # Полное имя
                "?"  # Премиум (пока заглушка)
            ]
            table_data.append(row)

        return table_data

    def get_ready_accounts(self) -> List[str]:
        """
        Возвращает аккаунты готовые к работе.
        Для главной страницы - это активные аккаунты трафика.
        """
        return self.get_accounts_by_status("traffic", "active")

    def get_total_counts(self) -> Dict[str, int]:
        """Возвращает общие счетчики"""
        traffic_accounts = self.get_accounts_by_category("traffic")
        sales_accounts = self.get_accounts_by_category("sales")

        return {
            "total": len(self.accounts),
            "traffic": len(traffic_accounts),
            "sales": len(sales_accounts)
        }

    def has_account(self, name: str) -> bool:
        """Проверяет существование аккаунта"""
        return name in self.accounts


# Глобальный экземпляр - единая точка доступа
_account_manager: Optional[AccountManager] = None


async def get_account_manager() -> AccountManager:
    """Получает глобальный экземпляр AccountManager"""
    global _account_manager
    if _account_manager is None:
        _account_manager = AccountManager()
        await _account_manager.scan_all_folders()  # Асинхронно сканируем
    return _account_manager


async def init_account_manager() -> AccountManager:
    """Инициализирует менеджер при старте приложения"""
    logger.info("🎯 Инициализация AccountManager...")
    manager = await get_account_manager()
    logger.info("✅ AccountManager готов!")
    return manager


# Функции для GUI (требуют менеджер уже инициализированным)
def get_traffic_stats() -> List[Tuple[str, str, str]]:
    """Быстрое получение статистики трафика"""
    if _account_manager:
        return _account_manager.get_traffic_stats()
    return [("Не загружено", "0", "#EF4444")]


def get_sales_stats() -> List[Tuple[str, str, str]]:
    """Быстрое получение статистики продаж"""
    if _account_manager:
        return _account_manager.get_sales_stats()
    return [("Не загружено", "0", "#EF4444")]


def get_table_data(category: str, limit: int = 50) -> List[List[str]]:
    """Быстрое получение данных таблицы"""
    if _account_manager:
        return _account_manager.get_table_data(category, limit)
    return []

