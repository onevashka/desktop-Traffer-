# src/accounts/operations/update_operations.py - ИСПРАВЛЕННАЯ ВЕРСИЯ
"""
Операции обновления аккаунтов - адаптировано под новую архитектуру с сервисами
"""

import asyncio
from loguru import logger
from typing import Dict


class AccountUpdater:
    """Класс для операций обновления аккаунтов"""

    def __init__(self, account_manager):
        self.manager = account_manager

    async def refresh_all_accounts(self) -> Dict[str, int]:
        """
        Полное обновление - пересканирование всех папок.

        Returns:
            Словарь с результатами обновления
        """
        logger.info("🔄 AccountUpdater: начинаем полное обновление аккаунтов...")

        # Сохраняем текущие счетчики
        old_traffic_count = len(self.manager.traffic_accounts)
        old_sales_count = len(self.manager.sales_accounts)

        # ИСПРАВЛЕНО: Используем метод менеджера вместо прямого вызова
        await self.manager.scan_all_folders()

        # Новые счетчики
        new_traffic_count = len(self.manager.traffic_accounts)
        new_sales_count = len(self.manager.sales_accounts)

        results = {
            'old_traffic': old_traffic_count,
            'new_traffic': new_traffic_count,
            'old_sales': old_sales_count,
            'new_sales': new_sales_count,
            'traffic_diff': new_traffic_count - old_traffic_count,
            'sales_diff': new_sales_count - old_sales_count
        }

        logger.info(f"✅ Обновление завершено:")
        logger.info(f"   Трафик: {old_traffic_count} → {new_traffic_count} ({results['traffic_diff']:+d})")
        logger.info(f"   Продажи: {old_sales_count} → {new_sales_count} ({results['sales_diff']:+d})")

        return results

    async def refresh_category(self, category: str) -> int:
        """
        Обновление конкретной категории.

        Returns:
            Количество загруженных аккаунтов
        """
        logger.info(f"🔄 AccountUpdater: обновляем категорию: {category}")

        if category == "traffic":
            storage = self.manager.traffic_accounts
        elif category == "sales":
            storage = self.manager.sales_accounts
        else:
            logger.error(f"❌ Неизвестная категория: {category}")
            return 0

        # Очищаем хранилище
        storage.clear()

        # ИСПРАВЛЕНО: Используем сервис сканера через менеджер
        scanner = self.manager._get_scanner()
        new_accounts = await scanner.scan_category(category)
        
        # Обновляем хранилище
        storage.update(new_accounts)
        
        # Обновляем сервисы менеджера
        self.manager._refresh_services()

        total_count = len(new_accounts)
        logger.info(f"✅ Категория {category} обновлена: {total_count} аккаунтов")
        return total_count