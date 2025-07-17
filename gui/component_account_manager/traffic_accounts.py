# gui/component_account_manager/traffic_accounts.py - ОБНОВЛЕННАЯ ВЕРСИЯ

"""
Компонент для работы с аккаунтами трафика с кликабельной статистикой
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout
from gui.component_account_manager.account_stats import AccountStatsWidget
from gui.component_account_manager.account_table import AccountTableWidget
from gui.component_account_manager.loading_animation import LoadingAnimationWidget
from src.accounts.manager import get_traffic_stats, get_table_data, get_default_status
from loguru import logger


class TrafficAccountsTab(QWidget):
    """Вкладка для управления аккаунтами трафика"""

    def __init__(self):
        super().__init__()
        self.setObjectName("TrafficAccountsTab")
        self.category = "traffic"
        self.current_status = get_default_status(self.category)  # "active" по умолчанию

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

        # Добавляем ключи статусов для кликабельности
        stats_with_keys = [
            (title, value, color, status_key) for (title, value, color), status_key in zip(
                traffic_stats,
                ["active", "dead", "frozen", "invalid"]
            )
        ]

        self.stats_widget = AccountStatsWidget(stats_with_keys, self.category)
        # Подключаем обработчик клика по статистике
        self.stats_widget.stat_clicked.connect(self._on_stat_clicked)
        self.main_content_layout.addWidget(self.stats_widget)

        # Таблица аккаунтов с реальными данными для текущей папки
        # ИСПРАВЛЕНО: Получаем ВСЕ данные для пагинации (без лимита)
        table_data = get_table_data(self.category, self.current_status, limit=-1)
        logger.debug(f"📋 Создаем таблицу трафика, данных: {len(table_data)} строк")

        table_config = {
            'title': '🚀 Аккаунты для трафика',
            'add_button_text': '+ Добавить аккаунт',
            'demo_data': table_data,
            'category': self.category,
            'current_status': self.current_status
        }

        self.table_widget = AccountTableWidget(table_config)
        self.main_content_layout.addWidget(self.table_widget)

    def _on_stat_clicked(self, status_key: str):
        """Обработка клика по статистике - переключение папки"""
        logger.info(f"🔄 Переключаемся на папку: {status_key}")

        self.current_status = status_key

        # Обновляем таблицу для новой папки
        self.table_widget.set_current_status(status_key)

        # Показываем уведомление о переключении
        try:
            from gui.notifications import show_info
            from src.accounts.manager import get_status_display_name, get_folder_status_count

            folder_name = get_status_display_name(self.category, status_key)
            count = get_folder_status_count(self.category, status_key)

            # Добавляем информацию о пагинации в уведомление
            pag_info = ""
            if hasattr(self.table_widget, 'get_pagination_info'):
                pag_data = self.table_widget.get_pagination_info()
                if pag_data['total_pages'] > 1:
                    pag_info = f"\n📄 Страница 1/{pag_data['total_pages']}"

            show_info(
                "Переключение папки",
                f"Показана папка: {folder_name}\nАккаунтов: {count}{pag_info}"
            )
        except Exception as e:
            logger.error(f"❌ Ошибка показа уведомления: {e}")

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

            # Обновляем таблицу для текущей папки
            # ИСПРАВЛЕНО: Получаем ВСЕ данные для пагинации
            new_table_data = get_table_data(self.category, self.current_status, limit=-1)
            self.table_widget.update_table_data(new_table_data)

            # Логируем информацию о пагинации
            if hasattr(self.table_widget, 'get_pagination_info'):
                pag_info = self.table_widget.get_pagination_info()
                logger.info(
                    f"📄 Пагинация трафика: {pag_info['current_page']}/{pag_info['total_pages']}, всего {pag_info['total_items']}")

            logger.info("✅ Данные трафика обновлены")

        except Exception as e:
            logger.error(f"❌ Ошибка обновления данных трафика: {e}")

    def get_current_status(self) -> str:
        """Возвращает текущий статус (папку)"""
        return self.current_status