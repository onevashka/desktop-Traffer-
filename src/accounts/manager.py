# src/accounts/manager.py - НОВАЯ ВЕРСИЯ
"""
Главный менеджер аккаунтов - координатор цеха
Делегирует задачи специализированным сервисам
"""

import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from loguru import logger

from src.entities.account import AccountData
from src.accounts.services import AccountScanner, StatisticsService, DataService, FolderService
from paths import *


class AccountManager:
    """
    Главный координатор цеха аккаунтов
    Делегирует задачи специализированным сервисам
    """

    def __init__(self):
        # Конфигурация папок
        self.traffic_folders = {
            "active": WORK_ACCOUNTS_TRAFFER_FOLDER,
            "dead": DEAD_TRAFFER_FOLDER,
            "frozen": FROZEN_TRAFFER_FOLDER,
            "invalid": INVALID_TRAFFER_FORMAT_FOLDER
        }

        self.sales_folders = {
            "registration": WORK_ACCOUNTS_SALE_FOLDER,
            "ready_tdata": TDATA_FOLDER,
            "ready_sessions": SESSIONS_JSON_FOLDER,
            "middle": MIDDLE_ACCOUNTS_FOLDER,
            "dead": DEAD_SALES_FOLDER,
            "frozen": FROZEN_SALES_FOLDER,
            "invalid": INVALID_SALES_FORMAT_FOLDER
        }

        # Хранилища данных
        self.traffic_accounts: Dict[str, AccountData] = {}
        self.sales_accounts: Dict[str, AccountData] = {}

        # Сервисы цеха (создаются лениво)
        self._scanner: Optional[AccountScanner] = None
        self._statistics: Optional[StatisticsService] = None
        self._data_service: Optional[DataService] = None
        self._folder_service: Optional[FolderService] = None

        # Операции (из существующего кода)
        self._deleter = None
        self._mover = None
        self._updater = None
        self._archiver = None

        logger.info("🏭 AccountManager цех инициализирован")

    # ═══════════════════════════════════════════════════════════════════
    # 🚀 ОСНОВНЫЕ МЕТОДЫ - делегируем сервисам
    # ═══════════════════════════════════════════════════════════════════

    async def scan_all_folders(self) -> None:
        """Полное сканирование всех папок"""
        scanner = self._get_scanner()
        storages = await scanner.scan_all_folders()

        self.traffic_accounts = storages['traffic']
        print(self.traffic_accounts)
        self.sales_accounts = storages['sales']

        # Обновляем зависимые сервисы
        self._refresh_services()

        logger.info(
            f"✅ Сканирование завершено: трафик={len(self.traffic_accounts)}, продажи={len(self.sales_accounts)}")

    def get_free_accounts(self, module_name: str, count: int = 1) -> List[AccountData]:
        """
        Универсальный метод получения свободных аккаунтов

        Args:
            module_name: Название модуля который запрашивает аккаунты
            count: Количество нужных аккаунтов (по умолчанию 1)

        Returns:
            Список AccountData (может быть меньше запрошенного если не хватает свободных)
        """
        if count <= 0:
            logger.warning(f"⚠️ Запрошено некорректное количество аккаунтов: {count}")
            return []

        accounts = []

        # Ищем среди активных аккаунтов трафика
        for account_name, account_data in self.traffic_accounts.items():
            if (account_data.status == "active" and
                    not account_data.is_busy):

                # Помечаем как занятый
                account_data.is_busy = True
                account_data.busy_by = module_name
                accounts.append(account_data)

                # Если набрали нужное количество - выходим
                if len(accounts) >= count:
                    break

        if accounts:
            logger.debug(f"🔒 Выдано аккаунтов для {module_name}: {len(accounts)} из {count}")
        else:
            logger.warning(f"⚠️ Нет свободных аккаунтов для {module_name}")

        return accounts

    def get_multiple_free_accounts(self, module_name: str, count: int) -> List[AccountData]:
        """
        Получает несколько свободных аккаунтов

        Args:
            module_name: Название модуля
            count: Количество нужных аккаунтов

        Returns:
            Список AccountData (может быть меньше запрошенного)
        """
        accounts = []

        for account_name, account_data in self.traffic_accounts.items():
            if (account_data.status == "active" and
                    not account_data.is_busy):

                # Помечаем как занятый
                account_data.is_busy = True
                account_data.busy_by = module_name
                accounts.append(account_data)

                if len(accounts) >= count:
                    break

        logger.debug(f"🔒 Выдано аккаунтов для {module_name}: {len(accounts)} из {count}")
        return accounts

    def release_account(self, account_name: str, module_name: str = None) -> bool:
        """
        Освобождает аккаунт

        Args:
            account_name: Имя аккаунта
            module_name: Модуль который освобождает (для проверки)

        Returns:
            True если успешно освобожден
        """
        if account_name not in self.traffic_accounts:
            logger.debug(f"❓ Аккаунт {account_name} не найден в трафике")
            return False

        account_data = self.traffic_accounts[account_name]

        if not account_data.is_busy:
            return True

        # Проверяем что освобождает тот же модуль
        if module_name and account_data.busy_by != module_name:
            logger.warning(f"⚠️ Модуль {module_name} пытается освободить чужой аккаунт {account_name}")
            return False

        # Освобождаем
        account_data.is_busy = False
        account_data.busy_by = None

        return True

    def release_all_module_accounts(self, module_name: str) -> int:
        """
        Освобождает все аккаунты занятые модулем

        Args:
            module_name: Название модуля

        Returns:
            Количество освобожденных аккаунтов
        """
        released_count = 0

        for account_name, account_data in self.traffic_accounts.items():
            if account_data.is_busy and account_data.busy_by == module_name:
                account_data.is_busy = False
                account_data.busy_by = None
                released_count += 1

        logger.info(f"🔓 Освобождено аккаунтов модуля {module_name}: {released_count}")
        return released_count

    def get_free_accounts_count(self) -> int:
        """
        Возвращает количество свободных активных аккаунтов

        Returns:
            Количество свободных аккаунтов
        """
        free_count = sum(
            1 for account_data in self.traffic_accounts.values()
            if account_data.status == "active" and not account_data.is_busy
        )
        return free_count

    def get_busy_accounts_info(self) -> List[Dict]:
        """
        Возвращает информацию о занятых аккаунтах

        Returns:
            Список словарей с информацией
        """
        busy_info = []

        for account_name, account_data in self.traffic_accounts.items():
            if account_data.is_busy:
                busy_info.append({
                    'name': account_name,
                    'busy_by': account_data.busy_by,
                    'phone': account_data.info.get('phone', '?'),
                    'full_name': account_data.info.get('full_name', '?')
                })

        return busy_info

    def is_account_busy(self, account_name: str) -> bool:
        """
        Проверяет занят ли аккаунт

        Args:
            account_name: Имя аккаунта

        Returns:
            True если занят
        """
        if account_name in self.traffic_accounts:
            return self.traffic_accounts[account_name].is_busy
        return False

    def reset_all_busy_status(self) -> int:
        """
        Сбрасывает статус занятости у всех аккаунтов
        Используется при старте приложения для очистки

        Returns:
            Количество сброшенных
        """
        reset_count = 0

        for account_data in self.traffic_accounts.values():
            if account_data.is_busy:
                account_data.is_busy = False
                account_data.busy_by = None
                reset_count += 1

        if reset_count > 0:
            logger.info(f"🧹 Сброшен статус занятости у {reset_count} аккаунтов")

        return reset_count




    # ═══════════════════════════════════════════════════════════════════
    # 📊 СТАТИСТИКА - делегируем StatisticsService
    # ═══════════════════════════════════════════════════════════════════

    def get_traffic_stats(self) -> List[Tuple[str, str, str]]:
        """Статистика трафика для GUI"""
        statistics = self._get_statistics()
        return statistics.get_traffic_stats()

    def get_sales_stats(self) -> List[Tuple[str, str, str]]:
        """Статистика продаж для GUI"""
        statistics = self._get_statistics()
        return statistics.get_sales_stats()

    def get_folder_counts(self) -> Dict[str, Dict[str, int]]:
        """Количество аккаунтов в каждой папке"""
        statistics = self._get_statistics()
        return statistics.get_folder_counts()

    def get_total_counts(self) -> Dict[str, int]:
        """Общие счетчики"""
        statistics = self._get_statistics()
        return statistics.get_total_counts()

    def get_folder_status_count(self, category: str, status: str) -> int:
        """Количество аккаунтов в конкретной папке"""
        statistics = self._get_statistics()
        return statistics.get_folder_status_count(category, status)

    # ═══════════════════════════════════════════════════════════════════
    # 📋 ДАННЫЕ ДЛЯ GUI - делегируем DataService
    # ═══════════════════════════════════════════════════════════════════

    def get_table_data(self, category: str, status: str = None, limit: int = 50) -> List[List[str]]:
        """Данные для таблицы GUI"""
        data_service = self._get_data_service()
        return data_service.get_table_data(category, status, limit)

    def get_paginated_data(self, category: str, status: str = None, page: int = 1, per_page: int = 10) -> dict:
        """Данные с пагинацией"""
        data_service = self._get_data_service()
        return data_service.get_paginated_data(category, status, page, per_page)

    def search_accounts(self, query: str, category: str = None, status: str = None) -> List[AccountData]:
        """Поиск аккаунтов"""
        data_service = self._get_data_service()
        return data_service.search_accounts(query, category, status)

    def get_account_by_name(self, name: str, category: str) -> Optional[AccountData]:
        """Получает аккаунт по имени"""
        data_service = self._get_data_service()
        return data_service.get_account_by_name(name, category)

    # ═══════════════════════════════════════════════════════════════════
    # 📁 РАБОТА С ПАПКАМИ - делегируем FolderService
    # ═══════════════════════════════════════════════════════════════════

    def get_default_status(self, category: str) -> str:
        """Статус по умолчанию для категории"""
        folder_service = self._get_folder_service()
        return folder_service.get_default_status(category)

    def get_status_display_name(self, category: str, status: str) -> str:
        """Человекочитаемое название статуса"""
        folder_service = self._get_folder_service()
        return folder_service.get_status_display_name(category, status)

    def get_move_destinations(self, current_category: str, current_status: str) -> List[Dict]:
        """Доступные папки для перемещения"""
        folder_service = self._get_folder_service()
        return folder_service.get_move_destinations(current_category, current_status)

    # ═══════════════════════════════════════════════════════════════════
    # ⚡ ОПЕРАЦИИ - делегируем существующим классам Operations
    # ═══════════════════════════════════════════════════════════════════

    def delete_accounts(self, account_names: List[str], category: str) -> Dict[str, bool]:
        """Удаление аккаунтов"""
        deleter = self._get_deleter()
        result = deleter.delete_accounts(account_names, category)
        self._refresh_services()  # Обновляем сервисы после изменений
        return result

    def get_account_info_for_deletion(self, account_names: List[str], category: str) -> List[Dict]:
        """Информация для подтверждения удаления"""
        deleter = self._get_deleter()
        return deleter.get_deletion_info(account_names, category)

    def move_accounts(self, account_names: List[str], source_category: str,
                      target_category: str, target_status: str) -> Dict[str, bool]:
        """Перемещение аккаунтов"""
        mover = self._get_mover()
        result = mover.move_accounts(account_names, source_category, target_category, target_status)
        self._refresh_services()
        return result

    def archive_accounts(self, account_names: List[str], category: str,
                         archive_name: str, archive_format: str) -> Dict[str, any]:
        """Архивация аккаунтов"""
        archiver = self._get_archiver()
        return archiver.archive_accounts(account_names, category, archive_name, archive_format)

    def get_account_info_for_archiving(self, account_names: List[str], category: str) -> List[Dict]:
        """Информация для архивации"""
        archiver = self._get_archiver()
        return archiver.get_archive_info(account_names, category)

    async def refresh_all_accounts(self) -> Dict[str, int]:
        """Полное обновление аккаунтов"""
        updater = self._get_updater()
        return await updater.refresh_all_accounts()

    async def refresh_category(self, category: str) -> int:
        """Обновление конкретной категории"""
        updater = self._get_updater()
        return await updater.refresh_category(category)

    # ═══════════════════════════════════════════════════════════════════
    # 🔧 ЛЕНИВАЯ ИНИЦИАЛИЗАЦИЯ СЕРВИСОВ
    # ═══════════════════════════════════════════════════════════════════

    def _get_scanner(self) -> AccountScanner:
        """Получает сканер (ленивая инициализация)"""
        if self._scanner is None:
            self._scanner = AccountScanner(self.traffic_folders, self.sales_folders)
        return self._scanner

    def _get_statistics(self) -> StatisticsService:
        """Получает статистический сервис"""
        if self._statistics is None:
            self._statistics = StatisticsService(self.traffic_accounts, self.sales_accounts)
        return self._statistics

    def _get_data_service(self) -> DataService:
        """Получает сервис данных"""
        print('fdsfds')
        if self._data_service is None:
            self._data_service = DataService(self.traffic_accounts, self.sales_accounts)
        return self._data_service

    def _get_folder_service(self) -> FolderService:
        """Получает сервис папок"""
        if self._folder_service is None:
            self._folder_service = FolderService(self.traffic_folders, self.sales_folders)
        return self._folder_service

    def _get_deleter(self):
        """Получает удалятор (из существующего кода)"""
        if self._deleter is None:
            from src.accounts.operations import AccountDeleter
            self._deleter = AccountDeleter(self)
        return self._deleter

    def _get_mover(self):
        """Получает переместитель (из существующего кода)"""
        if self._mover is None:
            from src.accounts.operations import AccountMover
            self._mover = AccountMover(self)
        return self._mover

    def _get_updater(self):
        """Получает обновлятор (из существующего кода)"""
        if self._updater is None:
            from src.accounts.operations import AccountUpdater
            self._updater = AccountUpdater(self)
        return self._updater

    def _get_archiver(self):
        """Получает архиватор (из существующего кода)"""
        if self._archiver is None:
            from src.accounts.operations.archive_operations import AccountArchiver
            self._archiver = AccountArchiver(self)
        return self._archiver

    def _refresh_services(self):
        """Обновляет сервисы после изменения данных"""
        self._statistics = None  # Пересоздастся с новыми данными
        self._data_service = None
        logger.debug("🔄 Сервисы обновлены")

    # ═══════════════════════════════════════════════════════════════════
    # 🔗 LEGACY API - для обратной совместимости
    # ═══════════════════════════════════════════════════════════════════

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

    def has_account(self, name: str, category: str) -> bool:
        """Проверяет существование аккаунта в определенной категории"""
        if category == "traffic":
            return name in self.traffic_accounts
        elif category == "sales":
            return name in self.sales_accounts
        else:
            return False

    def get_account(self, name: str, category: str = "traffic") -> Optional:
        """Возвращает объект Account по имени и категории"""

        account_data = self.get_account_by_name(name, category)
        print(account_data)
        return account_data.account if account_data else None

    def get_accounts_by_category(self, category: str) -> List[str]:
        """Возвращает список имен аккаунтов по категории"""
        if category == "traffic":
            return list(self.traffic_accounts.keys())
        elif category == "sales":
            return list(self.sales_accounts.keys())
        else:
            return []


# ═══════════════════════════════════════════════════════════════════
# 🌍 ГЛОБАЛЬНЫЙ ЭКЗЕМПЛЯР И ФУНКЦИИ ДЛЯ GUI
# ═══════════════════════════════════════════════════════════════════

_account_manager: Optional[AccountManager] = None


def get_free_accounts(module_name: str, count: int = 1) -> List[AccountData]:
    """
    Универсальная функция получения свободных аккаунтов

    Args:
        module_name: Название модуля
        count: Количество (по умолчанию 1)

    Returns:
        Список AccountData
    """
    global _account_manager
    if _account_manager:
        return _account_manager.get_free_accounts(module_name, count)
    return []


def get_multiple_free_accounts(module_name: str, count: int) -> List[AccountData]:
    """Быстрая функция получения нескольких аккаунтов"""
    global _account_manager
    if _account_manager:
        return _account_manager.get_multiple_free_accounts(module_name, count)
    return []


def release_account(account_name: str, module_name: str = None) -> bool:
    """Быстрая функция освобождения аккаунта"""
    global _account_manager
    if _account_manager:
        return _account_manager.release_account(account_name, module_name)
    return False


def release_all_module_accounts(module_name: str) -> int:
    """Быстрая функция освобождения всех аккаунтов модуля"""
    global _account_manager
    if _account_manager:
        return _account_manager.release_all_module_accounts(module_name)
    return 0


def get_free_accounts_count() -> int:
    """Быстрая функция подсчета свободных аккаунтов"""
    global _account_manager
    if _account_manager:
        return _account_manager.get_free_accounts_count()
    return 0


def reset_all_busy_status() -> int:
    """Сбрасывает все статусы занятости (при старте)"""
    global _account_manager
    if _account_manager:
        return _account_manager.reset_all_busy_status()
    return 0


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


# ═══════════════════════════════════════════════════════════════════
# 🎨 ФУНКЦИИ ДЛЯ GUI - простые обертки
# ═══════════════════════════════════════════════════════════════════

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


def get_paginated_data(category: str, status: str = None, page: int = 1, per_page: int = 10) -> dict:
    """Быстрое получение данных с пагинацией"""
    global _account_manager
    if _account_manager:
        return _account_manager.get_paginated_data(category, status, page, per_page)
    return {
        'data': [], 'total_items': 0, 'total_pages': 1, 'current_page': 1,
        'per_page': per_page, 'has_next': False, 'has_prev': False
    }


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


def get_account_info_for_archiving(account_names: List[str], category: str) -> List[Dict]:
    """Функция для GUI - получает информацию для архивации"""
    global _account_manager
    if _account_manager:
        return _account_manager.get_account_info_for_archiving(account_names, category)
    return []


def archive_accounts(account_names: List[str], category: str,
                     archive_name: str, archive_format: str) -> Dict[str, any]:
    """Функция для GUI - архивирует аккаунты"""
    global _account_manager
    if _account_manager:
        return _account_manager.archive_accounts(account_names, category, archive_name, archive_format)
    return {'success': False, 'message': 'Менеджер не инициализирован'}


def check_winrar_available() -> bool:
    """Функция для GUI - проверяет доступность WinRAR"""
    global _account_manager
    if _account_manager:
        archiver = _account_manager._get_archiver()
        return archiver.check_winrar_available()
    return False