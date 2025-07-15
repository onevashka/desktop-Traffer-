# TeleCRM/gui/components/sales_accounts.py
"""
Компонент для работы с аккаунтами продаж (только для организации)
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout
from gui.component_account_manager.account_stats import AccountStatsWidget
from gui.component_account_manager.account_table import AccountTableWidget
from gui.component_account_manager.loading_animation import LoadingAnimationWidget


class SalesAccountsTab(QWidget):
    """Вкладка для управления аккаунтами продаж"""

    def __init__(self):
        super().__init__()
        self.setObjectName("SalesAccountsTab")

        # Основной layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 15, 0, 0)
        layout.setSpacing(0)

        # Контейнер для основного контента
        self.main_content = QWidget()
        self.main_content.setObjectName("MainContent")
        self.main_content_layout = QVBoxLayout(self.main_content)
        self.main_content_layout.setContentsMargins(0, 0, 0, 0)
        self.main_content_layout.setSpacing(15)

        # Создаем компоненты
        self._create_components()

        # Анимация загрузки
        self.loading_widget = LoadingAnimationWidget("Загрузка склада аккаунтов...")

        # Добавляем в layout
        layout.addWidget(self.loading_widget)
        layout.addWidget(self.main_content)

        # Скрываем основной контент и запускаем загрузку
        self.main_content.hide()
        self.loading_widget.start_animation(self._show_main_content)

    def _create_components(self):
        """Создание компонентов вкладки продаж"""

        # Расширенная статистика с детализацией форматов
        sales_stats = [
            ("Регистрация", "0", "#3B82F6"),
            ("📁 TData", "0", "#10B981"),
            ("📄 Session+JSON", "0", "#059669"),
            ("Средних", "0", "#8B5CF6"),
            ("Замороженных", "0", "#F59E0B"),
            ("Мертвых", "0", "#EF4444")
        ]

        self.stats_widget = AccountStatsWidget(sales_stats)
        self.main_content_layout.addWidget(self.stats_widget)

        # Таблица аккаунтов продаж
        table_config = {
            'title': '💰 Склад аккаунтов для продажи',
            'add_button_text': '+ Добавить на склад',
            'demo_data': self._get_sales_demo_data()
        }

        self.table_widget = AccountTableWidget(table_config)
        self.main_content_layout.addWidget(self.table_widget)

    def _get_sales_demo_data(self):
        """Демо данные для аккаунтов продаж"""
        return [
            ["1", "@premium_acc_001", "RU", "156", "Готов", "Владимир П.", "✅"],
            ["2", "@quality_user_002", "US", "234", "В обработке", "Jessica Brown", "❌"],
            ["3", "@verified_acc_003", "DE", "89", "Готов", "Klaus Schmidt", "✅"],
            ["4", "@aged_account_004", "FR", "345", "Готов", "Antoine Moreau", "❌"],
            ["5", "@high_trust_005", "UK", "278", "Проверка", "Oliver Smith", "✅"],
            ["6", "@premium_user_006", "IT", "167", "Готов", "Giuseppe Rossi", "❌"],
            ["7", "@quality_acc_007", "ES", "198", "Готов", "Carmen Rodriguez", "✅"],
            ["8", "@verified_user_008", "CA", "145", "В обработке", "Michael Johnson", "❌"],
            ["9", "@aged_premium_009", "AU", "267", "Готов", "Rebecca Taylor", "✅"],
            ["10", "@trust_account_010", "NL", "134", "Готов", "Pieter de Vries", "❌"],
        ]

    def _show_main_content(self):
        """Показывает основной контент после загрузки"""
        self.loading_widget.hide()
        self.main_content.show()

        # Запускаем анимации компонентов
        self.stats_widget.animate_appearance()
        self.table_widget.animate_appearance()

    def refresh_data(self):
        """Обновляет данные аккаунтов продаж"""
        # TODO: Здесь будет загрузка реальных данных из склада
        pass