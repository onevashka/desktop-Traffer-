# src/accounts/services/statistics_service.py
"""
Статистический сервис - отвечает только за подсчет цифр и аналитику
"""

from typing import Dict, List, Tuple
from loguru import logger
from src.entities.account import AccountData


class StatisticsService:
    """Сервис для подсчета статистики по аккаунтам"""

    def __init__(self, traffic_accounts: Dict[str, AccountData], sales_accounts: Dict[str, AccountData]):
        self.traffic_accounts = traffic_accounts
        self.sales_accounts = sales_accounts
        logger.debug("📊 StatisticsService инициализирован")

    def get_traffic_stats(self) -> List[Tuple[str, str, str]]:
        """
        Статистика для GUI трафика

        Returns:
            List[Tuple[str, str, str]]: [(название, количество, цвет), ...]
        """
        counts = self._count_by_status(self.traffic_accounts)

        return [
            ("Активных аккаунтов", str(counts.get("active", 0)), "#10B981"),
            ("Мертвых", str(counts.get("dead", 0)), "#EF4444"),
            ("Замороженных", str(counts.get("frozen", 0)), "#F59E0B"),
            ("Неверный формат", str(counts.get("invalid", 0)), "#6B7280")
        ]

    def get_sales_stats(self) -> List[Tuple[str, str, str]]:
        """
        Статистика для GUI продаж

        Returns:
            List[Tuple[str, str, str]]: [(название, количество, цвет), ...]
        """
        counts = self._count_by_status(self.sales_accounts)

        return [
            ("Регистрация", str(counts.get("registration", 0)), "#3B82F6"),
            ("📁 TData", str(counts.get("ready_tdata", 0)), "#10B981"),
            ("📄 Session+JSON", str(counts.get("ready_sessions", 0)), "#059669"),
            ("Средних", str(counts.get("middle", 0)), "#8B5CF6"),
            ("Замороженных", str(counts.get("frozen", 0)), "#F59E0B"),
            ("Мертвых", str(counts.get("dead", 0)), "#EF4444")
        ]

    def get_folder_counts(self) -> Dict[str, Dict[str, int]]:
        """
        Возвращает количество аккаунтов в каждой папке

        Returns:
            Dict: {
                "traffic": {"active": 150, "dead": 45, ...},
                "sales": {"registration": 12, "ready_tdata": 25, ...}
            }
        """
        return {
            "traffic": self._count_by_status(self.traffic_accounts),
            "sales": self._count_by_status(self.sales_accounts)
        }

    def get_total_counts(self) -> Dict[str, int]:
        """
        Общие счетчики

        Returns:
            Dict: {"total": 336, "traffic": 247, "sales": 89}
        """
        return {
            "total": len(self.traffic_accounts) + len(self.sales_accounts),
            "traffic": len(self.traffic_accounts),
            "sales": len(self.sales_accounts)
        }

    def get_folder_status_count(self, category: str, status: str) -> int:
        """
        Количество аккаунтов в конкретной папке

        Args:
            category: "traffic" или "sales"
            status: Статус папки

        Returns:
            int: Количество аккаунтов
        """
        if category == "traffic":
            accounts = [data for data in self.traffic_accounts.values() if data.status == status]
        elif category == "sales":
            accounts = [data for data in self.sales_accounts.values() if data.status == status]
        else:
            return 0

        return len(accounts)

    def get_geo_stats(self, category: str = None) -> Dict[str, int]:
        """
        Статистика по географии

        Args:
            category: Фильтр по категории или None для всех

        Returns:
            Dict: {"RU": 89, "US": 35, "EU": 18, ...}
        """
        geo_counts = {}

        accounts_to_check = []
        if category == "traffic":
            accounts_to_check = list(self.traffic_accounts.values())
        elif category == "sales":
            accounts_to_check = list(self.sales_accounts.values())
        else:
            accounts_to_check = list(self.traffic_accounts.values()) + list(self.sales_accounts.values())

        for account_data in accounts_to_check:
            geo = account_data.info.get('geo', 'Unknown')
            geo_counts[geo] = geo_counts.get(geo, 0) + 1

        return geo_counts

    def get_premium_stats(self, category: str = None) -> Dict[str, int]:
        """
        Статистика по премиум аккаунтам

        Args:
            category: Фильтр по категории или None для всех

        Returns:
            Dict: {"premium": 23, "regular": 324}
        """
        premium_count = 0
        total_count = 0

        accounts_to_check = []
        if category == "traffic":
            accounts_to_check = list(self.traffic_accounts.values())
        elif category == "sales":
            accounts_to_check = list(self.sales_accounts.values())
        else:
            accounts_to_check = list(self.traffic_accounts.values()) + list(self.sales_accounts.values())

        for account_data in accounts_to_check:
            total_count += 1
            # TODO: добавить проверку премиум статуса когда будет реализовано
            # if account_data.info.get('is_premium', False):
            #     premium_count += 1

        return {
            "premium": premium_count,
            "regular": total_count - premium_count,
            "total": total_count
        }

    def get_status_distribution(self) -> Dict[str, Dict[str, int]]:
        """
        Распределение аккаунтов по статусам

        Returns:
            Dict: Детальная статистика по каждому статусу
        """
        traffic_counts = self._count_by_status(self.traffic_accounts)
        sales_counts = self._count_by_status(self.sales_accounts)

        # Объединяем статистику
        all_statuses = set(traffic_counts.keys()) | set(sales_counts.keys())

        distribution = {}
        for status in all_statuses:
            distribution[status] = {
                "traffic": traffic_counts.get(status, 0),
                "sales": sales_counts.get(status, 0),
                "total": traffic_counts.get(status, 0) + sales_counts.get(status, 0)
            }

        return distribution

    def _count_by_status(self, accounts: Dict[str, AccountData]) -> Dict[str, int]:
        """
        Подсчитывает аккаунты по статусам

        Args:
            accounts: Словарь аккаунтов

        Returns:
            Dict: {"active": 150, "dead": 45, ...}
        """
        counts = {}
        for account_data in accounts.values():
            status = account_data.status
            counts[status] = counts.get(status, 0) + 1
        return counts

    def get_detailed_stats_report(self) -> Dict:
        """
        Подробный отчет по всем статистикам

        Returns:
            Dict: Полный отчет для экспорта или детального просмотра
        """
        return {
            "summary": self.get_total_counts(),
            "traffic_stats": dict(zip(
                [item[0] for item in self.get_traffic_stats()],
                [int(item[1]) for item in self.get_traffic_stats()]
            )),
            "sales_stats": dict(zip(
                [item[0] for item in self.get_sales_stats()],
                [int(item[1]) for item in self.get_sales_stats()]
            )),
            "folder_counts": self.get_folder_counts(),
            "geo_distribution": self.get_geo_stats(),
            "premium_stats": self.get_premium_stats(),
            "status_distribution": self.get_status_distribution()
        }