# TeleCRM/gui/components/traffic_accounts.py
"""
Компонент для работы с аккаунтами трафика
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout
from gui.component_account_manager.account_stats import AccountStatsWidget
from gui.component_account_manager.account_table import AccountTableWidget
from gui.component_account_manager.loading_animation import LoadingAnimationWidget


class TrafficAccountsTab(QWidget):
    """Вкладка для управления аккаунтами трафика"""

    def __init__(self):
        super().__init__()
        self.setObjectName("TrafficAccountsTab")

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
        self.loading_widget = LoadingAnimationWidget("Загрузка аккаунтов трафика...")

        # Добавляем в layout
        layout.addWidget(self.loading_widget)
        layout.addWidget(self.main_content)

        # Скрываем основной контент и запускаем загрузку
        self.main_content.hide()
        self.loading_widget.start_animation(self._show_main_content)

    def _create_components(self):
        """Создание компонентов вкладки"""

        # Статистика для трафика (пока статичные данные)
        traffic_stats = [
            ("Активных аккаунтов", "0", "#10B981"),
            ("Мертвых", "0", "#EF4444"),
            ("Замороженных", "0", "#F59E0B"),
            ("Неверный формат", "0", "#6B7280")
        ]

        self.stats_widget = AccountStatsWidget(traffic_stats)
        self.main_content_layout.addWidget(self.stats_widget)

        # Таблица аккаунтов
        table_config = {
            'title': '🚀 Аккаунты для трафика',
            'add_button_text': '+ Добавить аккаунт',
            'demo_data': self._get_traffic_demo_data()
        }

        self.table_widget = AccountTableWidget(table_config)
        self.main_content_layout.addWidget(self.table_widget)

    def _get_traffic_demo_data(self):
        """Демо данные для аккаунтов трафика"""
        return [
            ["1", "@traffic_user_1", "RU", "23", "2 мин назад", "Алексей Т.", "✅"],
            ["2", "@promo_account", "US", "45", "10 мин назад", "Mike Johnson", "❌"],
            ["3", "@marketing_bot", "DE", "12", "1 час назад", "Hans Weber", "✅"],
            ["4", "@ads_manager", "FR", "67", "3 часа назад", "Pierre Dubois", "❌"],
            ["5", "@content_creator", "UK", "34", "5 часов назад", "Emma Wilson", "✅"],
            ["6", "@traffic_gen", "IT", "89", "1 день назад", "Marco Rossi", "❌"],
            ["7", "@seo_specialist", "ES", "56", "2 дня назад", "Carlos Garcia", "✅"],
            ["8", "@affiliate_pro", "CA", "78", "3 дня назад", "John Smith", "❌"],
            ["9", "@media_buyer", "AU", "45", "1 неделя назад", "Sarah Connor", "✅"],
            ["10", "@conversion_opt", "NL", "23", "2 недели назад", "Jan van Berg", "❌"],
        ]

    def _show_main_content(self):
        """Показывает основной контент после загрузки"""
        self.loading_widget.hide()
        self.main_content.show()

        # Запускаем анимации компонентов
        self.stats_widget.animate_appearance()
        self.table_widget.animate_appearance()

    def refresh_data(self):
        """Обновляет данные аккаунтов трафика"""
        # TODO: Здесь будет загрузка реальных данных
        pass