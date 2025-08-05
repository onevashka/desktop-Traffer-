# src/accounts/services/data_service.py
"""
Сервис данных - отвечает за подготовку данных для GUI в нужном формате
"""

from typing import Dict, List, Optional
from loguru import logger
from src.entities.account import AccountData


class DataService:
    """Сервис для предоставления данных GUI в нужном формате"""

    def __init__(self, traffic_accounts: Dict[str, AccountData], sales_accounts: Dict[str, AccountData]):
        self.traffic_accounts = traffic_accounts
        self.sales_accounts = sales_accounts
        logger.debug("📋 DataService инициализирован")

    def get_table_data(self, category: str, status: str = None, limit: int = 50) -> List[List[str]]:
        """
        Данные для таблицы GUI

        Args:
            category: "traffic" или "sales"
            status: конкретный статус (папка) или None для всех
            limit: максимальное количество записей, -1 для всех данных

        Returns:
            List[List[str]]: Строки таблицы
        """
        logger.debug(f"📋 Получаем данные таблицы: {category}/{status}, limit={limit}")

        # Выбираем хранилище
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

        # Сортируем по имени для стабильного порядка
        category_accounts.sort(key=lambda x: x.name)

        # Ограничиваем количество только если limit > 0
        if limit > 0:
            category_accounts = category_accounts[:limit]

        # Формируем данные таблицы
        table_data = []
        for account_data in category_accounts:
            row = self._format_table_row(account_data)
            table_data.append(row)

        logger.debug(f"📊 Получены данные для {category}/{status}: {len(table_data)} записей (limit={limit})")
        return table_data

    def get_paginated_data(self, category: str, status: str = None, page: int = 1, per_page: int = 10) -> dict:
        """
        Данные с пагинацией

        Args:
            category: "traffic" или "sales"
            status: конкретный статус (папка) или None для всех
            page: номер страницы (начиная с 1)
            per_page: количество записей на странице

        Returns:
            dict: {
                'data': List[List[str]],  # Данные для текущей страницы
                'total_items': int,       # Общее количество записей
                'total_pages': int,       # Общее количество страниц
                'current_page': int,      # Текущая страница
                'per_page': int,          # Записей на странице
                'has_next': bool,         # Есть ли следующая страница
                'has_prev': bool          # Есть ли предыдущая страница
            }
        """
        logger.debug(f"📄 Получаем пагинированные данные: {category}/{status}, страница {page}, по {per_page}")

        # Получаем все данные
        all_data = self.get_table_data(category, status, limit=-1)
        total_items = len(all_data)

        # Рассчитываем пагинацию
        if per_page <= 0:
            per_page = total_items or 1

        total_pages = max(1, (total_items + per_page - 1) // per_page) if total_items > 0 else 1

        # Корректируем номер страницы
        if page < 1:
            page = 1
        elif page > total_pages:
            page = total_pages

        # Получаем данные для текущей страницы
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        page_data = all_data[start_idx:end_idx]

        result = {
            'data': page_data,
            'total_items': total_items,
            'total_pages': total_pages,
            'current_page': page,
            'per_page': per_page,
            'has_next': page < total_pages,
            'has_prev': page > 1
        }

        logger.debug(
            f"📄 Пагинация {category}/{status}: страница {page}/{total_pages}, показано {len(page_data)} из {total_items}")
        return result

    def get_account_by_name(self, name: str, category: str) -> Optional[AccountData]:
        """
        Получает аккаунт по имени и категории

        Args:
            name: Имя аккаунта
            category: Категория аккаунта

        Returns:
            AccountData или None если не найден
        """
        if category == "traffic":
            print(self.traffic_accounts)
            return self.traffic_accounts.get(name)
        elif category == "sales":
            return self.sales_accounts.get(name)
        else:
            return None

    def search_accounts(self, query: str, category: str = None, status: str = None) -> List[AccountData]:
        """
        Поиск аккаунтов по запросу

        Args:
            query: Поисковый запрос
            category: Фильтр по категории или None для всех
            status: Фильтр по статусу или None для всех

        Returns:
            List[AccountData]: Найденные аккаунты
        """
        logger.debug(f"🔍 Поиск аккаунтов: '{query}', category={category}, status={status}")

        # Выбираем аккаунты для поиска
        accounts_to_search = []
        if category == "traffic":
            accounts_to_search = list(self.traffic_accounts.values())
        elif category == "sales":
            accounts_to_search = list(self.sales_accounts.values())
        else:
            accounts_to_search = list(self.traffic_accounts.values()) + list(self.sales_accounts.values())

        # Фильтр по статусу
        if status:
            accounts_to_search = [acc for acc in accounts_to_search if acc.status == status]

        # Поиск
        query_lower = query.lower()
        found_accounts = []

        for account_data in accounts_to_search:
            if self._matches_query(account_data, query_lower):
                found_accounts.append(account_data)

        logger.debug(f"🔍 Найдено аккаунтов: {len(found_accounts)}")
        return found_accounts

    def get_accounts_by_filter(self, filters: Dict) -> List[AccountData]:
        """
        Получает аккаунты по фильтрам

        Args:
            filters: Словарь фильтров {
                'category': 'traffic'|'sales'|None,
                'status': str|None,
                'geo': str|None,
                'has_phone': bool|None,
                'is_premium': bool|None
            }

        Returns:
            List[AccountData]: Отфильтрованные аккаунты
        """
        # Выбираем аккаунты
        accounts_to_filter = []
        category = filters.get('category')

        if category == "traffic":
            accounts_to_filter = list(self.traffic_accounts.values())
        elif category == "sales":
            accounts_to_filter = list(self.sales_accounts.values())
        else:
            accounts_to_filter = list(self.traffic_accounts.values()) + list(self.sales_accounts.values())

        # Применяем фильтры
        filtered_accounts = []
        for account_data in accounts_to_filter:
            if self._matches_filters(account_data, filters):
                filtered_accounts.append(account_data)

        return filtered_accounts

    def _format_table_row(self, account_data: AccountData) -> List[str]:
        """
        Форматирует строку таблицы

        Args:
            account_data: Данные аккаунта

        Returns:
            List[str]: Строка таблицы
        """
        info = account_data.info

        # Статус для отображения
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

        return [
            info.get('session_name', account_data.name),  # Название
            info.get('geo', '?'),  # Гео
            "?",  # Дней создан (TODO)
            status_display,  # Статус
            info.get('full_name', '?') or '?',  # Имя
            info.get('phone', '?') or '?',  # Телефон
            "❓"  # Премиум (TODO)
        ]

    def _matches_query(self, account_data: AccountData, query_lower: str) -> bool:
        """
        Проверяет соответствует ли аккаунт поисковому запросу

        Args:
            account_data: Данные аккаунта
            query_lower: Поисковый запрос в нижнем регистре

        Returns:
            bool: True если соответствует
        """
        info = account_data.info

        # Поиск по различным полям
        searchable_fields = [
            account_data.name.lower(),
            info.get('session_name', '').lower(),
            info.get('full_name', '').lower(),
            info.get('phone', '').lower(),
            info.get('geo', '').lower(),
            account_data.status.lower()
        ]

        # Проверяем каждое поле
        for field in searchable_fields:
            if query_lower in field:
                return True

        return False

    def _matches_filters(self, account_data: AccountData, filters: Dict) -> bool:
        """
        Проверяет соответствует ли аккаунт фильтрам

        Args:
            account_data: Данные аккаунта
            filters: Словарь фильтров

        Returns:
            bool: True если соответствует всем фильтрам
        """
        info = account_data.info

        # Фильтр по статусу
        if filters.get('status') and account_data.status != filters['status']:
            return False

        # Фильтр по гео
        if filters.get('geo') and info.get('geo', '') != filters['geo']:
            return False

        # Фильтр по наличию телефона
        if filters.get('has_phone') is not None:
            has_phone = bool(info.get('phone', '').strip())
            if has_phone != filters['has_phone']:
                return False

        # Фильтр по премиум (когда будет реализовано)
        if filters.get('is_premium') is not None:
            # TODO: добавить проверку премиум статуса
            pass

        return True