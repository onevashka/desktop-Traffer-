# src/accounts/manager.py - ИСПРАВЛЕННАЯ ВЕРСИЯ

"""
Центральный AccountManager - раздельные хранилища для трафика и продаж
"""

import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from loguru import logger

from src.entities.account import AccountData
from src.accounts.impl.account import Account
from paths import *


class AccountManager:
    """
    Центральный менеджер аккаунтов.
    Раздельные хранилища для трафика и продаж.
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

        # ИЗМЕНЕНО: Раздельные хранилища
        self.traffic_accounts: Dict[str, AccountData] = {}
        self.sales_accounts: Dict[str, AccountData] = {}

        self.deleter = None
        self.mover = None
        self.updater = None

        logger.info("📋 AccountManager создан с раздельными хранилищами")

    def _init_operations(self):
        """Инициализирует объекты операций (ленивая инициализация)"""
        if not self.deleter:
            from src.accounts.operations import AccountDeleter, AccountMover, AccountUpdater
            self.deleter = AccountDeleter(self)
            self.mover = AccountMover(self)
            self.updater = AccountUpdater(self)

    async def scan_all_folders(self) -> None:
        """
        Сканирует все папки и создает объекты Account.
        Раздельно для трафика и продаж.
        """
        logger.info("🔍 Начинаем полное сканирование и загрузку аккаунтов...")

        self.traffic_accounts.clear()
        self.sales_accounts.clear()

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

        total = len(self.traffic_accounts) + len(self.sales_accounts)
        logger.info(f"✅ Полная загрузка завершена! Трафик: {traffic_total}, Продажи: {sales_total}, Всего: {total}")

    async def _scan_folder(self, folder_path: Path, category: str, status: str) -> int:
        """
        Сканирует папку и создает объекты Account.
        Сохраняет в соответствующее хранилище.
        """
        if not folder_path.exists():
            logger.debug(f"⏭️  Папка не существует: {folder_path}")
            return 0

        logger.debug(f"🔍 Сканируем папку: {folder_path} (категория: {category}, статус: {status})")

        # ИЗМЕНЕНО: Выбираем правильное хранилище
        if category == "traffic":
            accounts_storage = self.traffic_accounts
        elif category == "sales":
            accounts_storage = self.sales_accounts
        else:
            logger.error(f"❌ Неизвестная категория: {category}")
            return 0

        count = 0
        try:
            session_files = list(folder_path.glob("*.session"))
            logger.debug(f"📁 Найдено .session файлов: {len(session_files)}")

            for session_file in session_files:
                json_file = session_file.with_suffix(".json")

                if json_file.exists():
                    name = session_file.stem

                    # ИЗМЕНЕНО: Проверяем дубликаты только в рамках категории
                    if name in accounts_storage:
                        logger.warning(f"⚠️  Дубликат в {category}: {name}")
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

                        # ИЗМЕНЕНО: Сохраняем в соответствующее хранилище
                        accounts_storage[name] = account_data
                        count += 1

                        logger.debug(
                            f"  ✅ Загружен в {category}: {name} | {info.get('full_name', '?')} | {info.get('phone', '?')}")

                    except Exception as e:
                        logger.error(f"❌ Ошибка создания Account для {name}: {e}")
                        continue
                else:
                    logger.debug(f"⚠️  JSON файл не найден для: {session_file.name}")

        except Exception as e:
            logger.error(f"❌ Ошибка сканирования {folder_path}: {e}")

        logger.debug(f"📊 Папка {folder_path.name}: загружено {count} аккаунтов")
        return count

    def get_folder_counts(self) -> Dict[str, Dict[str, int]]:
        """Возвращает количество аккаунтов в каждой папке"""
        counts = {
            "traffic": {status: 0 for status in self.traffic_folders.keys()},
            "sales": {status: 0 for status in self.sales_folders.keys()}
        }

        # ИЗМЕНЕНО: Считаем раздельно
        for account_data in self.traffic_accounts.values():
            if account_data.status in counts["traffic"]:
                counts["traffic"][account_data.status] += 1

        for account_data in self.sales_accounts.values():
            if account_data.status in counts["sales"]:
                counts["sales"][account_data.status] += 1

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

        return [
            ("Регистрация", str(counts["registration"]), "#3B82F6"),
            ("📁 TData", str(counts["ready_tdata"]), "#10B981"),
            ("📄 Session+JSON", str(counts["ready_sessions"]), "#059669"),
            ("Средних", str(counts["middle"]), "#8B5CF6"),
            ("Замороженных", str(counts["frozen"]), "#F59E0B"),
            ("Мертвых", str(counts["dead"]), "#EF4444")
        ]

    def get_table_data(self, category: str, status: str = None, limit: int = 50) -> List[List[str]]:
        """
        Возвращает данные для отображения в таблице

        Args:
            category: "traffic" или "sales"
            status: конкретный статус (папка) или None для всех
            limit: максимальное количество записей
        """

        # Выбираем правильное хранилище
        if category == "traffic":
            accounts_storage = self.traffic_accounts
        elif category == "sales":
            accounts_storage = self.sales_accounts
        else:
            logger.error(f"❌ Неизвестная категория: {category}")
            return []

        # Фильтруем по статусу если указан
        if status:
            category_accounts = [
                data for data in accounts_storage.values()
                if data.status == status
            ]
        else:
            category_accounts = list(accounts_storage.values())

        # Ограничиваем количество
        category_accounts = category_accounts[:limit]

        table_data = []
        for i, account_data in enumerate(category_accounts, 1):
            info = account_data.info

            # Определяем статус для отображения
            status_display = {
                "active": "✅ Активный",
                "dead": "❌ Мертвый",
                "frozen": "🧊 Заморожен",
                "invalid": "⚠️ Неверный формат",
                "registration": "📝 Регистрация",
                "ready_tdata": "📁 TData готов",
                "ready_sessions": "📄 Session готов",
                "middle": "🟡 Средний"
            }.get(account_data.status, account_data.status)

            # Формируем строку таблицы с реальными данными
            session_name = info.get('session_name', account_data.name)

            row = [
                str(i),  # Номер
                session_name,  # Чистое имя файла
                info.get('geo', '?'),  # Гео из номера телефона
                "?",  # Дней создан (пока заглушка)
                status_display,  # Статус аккаунта
                info.get('full_name', '?') or '?',  # Полное имя
                "❓"  # Премиум (пока заглушка)
            ]
            table_data.append(row)

        return table_data

    # НОВЫЕ МЕТОДЫ для поддержки папок
    def get_default_status(self, category: str) -> str:
        """Возвращает статус по умолчанию для категории"""
        if category == "traffic":
            return "active"  # Показываем активные аккаунты
        elif category == "sales":
            return "registration"  # Показываем регистрационные аккаунты
        else:
            return "active"

    def get_status_display_name(self, category: str, status: str) -> str:
        """Возвращает человекочитаемое название статуса"""
        display_names = {
            "traffic": {
                "active": "Активные аккаунты",
                "dead": "Мертвые аккаунты",
                "frozen": "Замороженные аккаунты",
                "invalid": "Неверный формат"
            },
            "sales": {
                "registration": "Регистрационные аккаунты",
                "ready_tdata": "TData готовые",
                "ready_sessions": "Session+JSON готовые",
                "middle": "Средние аккаунты",
                "dead": "Мертвые аккаунты",
                "frozen": "Замороженные аккаунты",
                "invalid": "Неверный формат"
            }
        }

        return display_names.get(category, {}).get(status, f"Аккаунты ({status})")

    def get_folder_status_count(self, category: str, status: str) -> int:
        """Возвращает количество аккаунтов в конкретной папке"""
        if category == "traffic":
            accounts = [data for data in self.traffic_accounts.values() if data.status == status]
        elif category == "sales":
            accounts = [data for data in self.sales_accounts.values() if data.status == status]
        else:
            return 0

        return len(accounts)

    def get_accounts_by_category(self, category: str) -> List[str]:
        """Возвращает список имен аккаунтов по категории"""
        if category == "traffic":
            return list(self.traffic_accounts.keys())
        elif category == "sales":
            return list(self.sales_accounts.keys())
        else:
            return []

    def get_account(self, name: str, category: str) -> Optional[Account]:
        """Возвращает объект Account по имени и категории"""
        if category == "traffic":
            account_data = self.traffic_accounts.get(name)
        elif category == "sales":
            account_data = self.sales_accounts.get(name)
        else:
            return None

        return account_data.account if account_data else None

    def has_account(self, name: str, category: str) -> bool:
        """Проверяет существование аккаунта в определенной категории"""
        if category == "traffic":
            return name in self.traffic_accounts
        elif category == "sales":
            return name in self.sales_accounts
        else:
            return False

    @property
    def accounts(self) -> Dict[str, AccountData]:
        """
        Объединенный словарь всех аккаунтов для обратной совместимости.
        Использует префиксы для уникальности.
        """
        combined = {}

        # Добавляем трафик с префиксом
        for name, data in self.traffic_accounts.items():
            combined[f"traffic_{name}"] = data

        # Добавляем продажи с префиксом
        for name, data in self.sales_accounts.items():
            combined[f"sales_{name}"] = data

        return combined

    def get_total_counts(self) -> Dict[str, int]:
        """Возвращает общие счетчики"""
        return {
            "total": len(self.traffic_accounts) + len(self.sales_accounts),
            "traffic": len(self.traffic_accounts),
            "sales": len(self.sales_accounts)
        }

    def delete_accounts(self, account_names: List[str], category: str) -> Dict[str, bool]:
        """Удаляет аккаунты"""
        self._init_operations()
        return self.deleter.delete_accounts(account_names, category)

    def get_account_info_for_deletion(self, account_names: List[str], category: str) -> List[Dict]:
        """Получает информацию для подтверждения удаления"""
        self._init_operations()
        return self.deleter.get_deletion_info(account_names, category)

    def move_accounts(self, account_names: List[str], source_category: str,
                      target_category: str, target_status: str) -> Dict[str, bool]:
        """Перемещает аккаунты"""
        self._init_operations()
        return self.mover.move_accounts(account_names, source_category, target_category, target_status)

    def get_move_destinations(self, current_category: str, current_status: str) -> List[Dict]:
        """Получает список доступных папок для перемещения"""
        self._init_operations()
        return self.mover.get_available_destinations(current_category, current_status)

    async def refresh_all_accounts(self) -> Dict[str, int]:
        """Полное обновление аккаунтов"""
        self._init_operations()
        return await self.updater.refresh_all_accounts()

    async def refresh_category(self, category: str) -> int:
        """Обновление конкретной категории"""
        self._init_operations()
        return await self.updater.refresh_category(category)


# ИСПРАВЛЕНО: Глобальный экземпляр и функции
_account_manager: Optional[AccountManager] = None


async def get_account_manager() -> AccountManager:
    """Получает глобальный экземпляр AccountManager"""
    global _account_manager
    if _account_manager is None:
        _account_manager = AccountManager()
        await _account_manager.scan_all_folders()
    return _account_manager


async def init_account_manager() -> AccountManager:
    """Инициализирует менеджер при старте приложения"""
    global _account_manager
    logger.info("🎯 Инициализация AccountManager...")
    _account_manager = await get_account_manager()
    logger.info("✅ AccountManager готов!")
    return _account_manager


# ИСПРАВЛЕНО: Функции для GUI
def get_traffic_stats() -> List[Tuple[str, str, str]]:
    """Быстрое получение статистики трафика"""
    global _account_manager
    if _account_manager:
        return _account_manager.get_traffic_stats()
    return [("Не загружено", "0", "#EF4444")]


def get_sales_stats() -> List[Tuple[str, str, str]]:
    """Быстрое получение статистики продаж"""
    global _account_manager
    if _account_manager:
        return _account_manager.get_sales_stats()
    return [("Не загружено", "0", "#EF4444")]


def get_table_data(category: str, status: str = None, limit: int = 50) -> List[List[str]]:
    """Быстрое получение данных таблицы"""
    global _account_manager
    if _account_manager:
        return _account_manager.get_table_data(category, status, limit)
    return []


def get_default_status(category: str) -> str:
    """Возвращает статус по умолчанию для категории"""
    global _account_manager
    if _account_manager:
        return _account_manager.get_default_status(category)
    return "active" if category == "traffic" else "registration"


def get_status_display_name(category: str, status: str) -> str:
    """Возвращает человекочитаемое название статуса"""
    global _account_manager
    if _account_manager:
        return _account_manager.get_status_display_name(category, status)
    return f"Аккаунты ({status})"


def get_folder_status_count(category: str, status: str) -> int:
    """Возвращает количество аккаунтов в конкретной папке"""
    global _account_manager
    if _account_manager:
        return _account_manager.get_folder_status_count(category, status)
    return 0


def delete_accounts(account_names: List[str], category: str) -> Dict[str, bool]:
    """Функция для GUI - удаляет аккаунты"""
    global _account_manager
    if _account_manager:
        return _account_manager.delete_accounts(account_names, category)
    return {name: False for name in account_names}


def get_account_info_for_deletion(account_names: List[str], category: str) -> List[Dict]:
    """Функция для GUI - получает информацию для удаления"""
    global _account_manager
    if _account_manager:
        return _account_manager.get_account_info_for_deletion(account_names, category)
    return []


def move_accounts(account_names: List[str], source_category: str,
                  target_category: str, target_status: str) -> Dict[str, bool]:
    """Функция для GUI - перемещает аккаунты"""
    global _account_manager
    if _account_manager:
        return _account_manager.move_accounts(account_names, source_category, target_category, target_status)
    return {name: False for name in account_names}


def get_move_destinations(current_category: str, current_status: str) -> List[Dict]:
    """Функция для GUI - получает назначения для перемещения"""
    global _account_manager
    if _account_manager:
        return _account_manager.get_move_destinations(current_category, current_status)
    return []


async def refresh_all_accounts() -> Dict[str, int]:
    """Функция для GUI - полное обновление"""
    global _account_manager
    if _account_manager:
        return await _account_manager.refresh_all_accounts()
    return {"error": True}


async def refresh_category(category: str) -> int:
    """Функция для GUI - обновление категории"""
    global _account_manager
    if _account_manager:
        return await _account_manager.refresh_category(category)
    return 0