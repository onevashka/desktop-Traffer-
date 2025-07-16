"""
Операции обновления аккаунтов
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
        logger.info("🔄 Начинаем полное обновление аккаунтов...")

        # Сохраняем текущие счетчики
        old_traffic_count = len(self.manager.traffic_accounts)
        old_sales_count = len(self.manager.sales_accounts)

        # Пересканируем все папки
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
        logger.info(f"🔄 Обновляем категорию: {category}")

        if category == "traffic":
            storage = self.manager.traffic_accounts
            folders = self.manager.traffic_folders
        elif category == "sales":
            storage = self.manager.sales_accounts
            folders = self.manager.sales_folders
        else:
            logger.error(f"❌ Неизвестная категория: {category}")
            return 0

        # Очищаем хранилище
        storage.clear()

        # Пересканируем папки категории
        total_count = 0
        for status, folder_path in folders.items():
            count = await self.manager._scan_folder(folder_path, category, status)
            total_count += count

        logger.info(f"✅ Категория {category} обновлена: {total_count} аккаунтов")
        return total_count
