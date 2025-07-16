# gui/component_account_manager/traffic_accounts.py - СТАБИЛЬНАЯ ВЕРСИЯ

"""
Компонент для работы с аккаунтами трафика - стабильная версия
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout
from gui.component_account_manager.account_stats import AccountStatsWidget
from gui.component_account_manager.account_table import AccountTableWidget
from gui.component_account_manager.loading_animation import LoadingAnimationWidget
from src.accounts.manager import get_traffic_stats, get_table_data
from loguru import logger


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

        # Получаем реальную статистику из AccountManager
        traffic_stats = get_traffic_stats()
        logger.debug(f"📊 Создаем компоненты трафика, статистика: {traffic_stats}")

        self.stats_widget = AccountStatsWidget(traffic_stats)
        self.main_content_layout.addWidget(self.stats_widget)

        # Таблица аккаунтов с реальными данными
        table_data = get_table_data("traffic", limit=50)
        logger.debug(f"📋 Создаем таблицу трафика, данных: {len(table_data)} строк")

        table_config = {
            'title': '🚀 Аккаунты для трафика',
            'add_button_text': '+ Добавить аккаунт',
            'demo_data': table_data
        }

        self.table_widget = AccountTableWidget(table_config)
        self.main_content_layout.addWidget(self.table_widget)

    def _show_main_content(self):
        """Показывает основной контент после загрузки"""
        self.loading_widget.hide()
        self.main_content.show()

        # Запускаем анимации компонентов
        self.stats_widget.animate_appearance()
        self.table_widget.animate_appearance()

    def refresh_data(self):
        """Обновляет данные аккаунтов трафика"""
        try:
            logger.info("🔄 Обновляем данные трафика...")

            # Получаем новую статистику
            new_stats = get_traffic_stats()
            logger.debug(f"📊 Новая статистика: {new_stats}")

            # Обновляем каждый элемент статистики
            for i, (title, value, color) in enumerate(new_stats):
                if i < len(self.stats_widget.stat_boxes):
                    self.stats_widget.update_stat(i, value)
                    logger.debug(f"   📊 Обновлен элемент {i}: {title} = {value}")

            # Получаем новые данные таблицы
            new_data = get_table_data("traffic", limit=50)
            logger.debug(f"📋 Новые данные таблицы: {len(new_data)} строк")

            # Обновляем таблицу
            if hasattr(self.table_widget, 'update_table_data'):
                self.table_widget.update_table_data(new_data)
                logger.info("✅ Данные трафика обновлены через update_table_data")
            else:
                # Fallback метод
                self.table_widget.config['demo_data'] = new_data
                if hasattr(self.table_widget, '_fill_table_data'):
                    self.table_widget._fill_table_data()
                logger.info("✅ Данные трафика обновлены через fallback")

        except Exception as e:
            logger.error(f"❌ Ошибка обновления данных трафика: {e}")
            # НЕ показываем уведомление об ошибке в refresh_data - пусть вызывающий код решает