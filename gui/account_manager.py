# TeleCRM/gui/account_manager.py
"""
Главный менеджер аккаунтов с системой вкладок
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QLabel
)
from PySide6.QtCore import Qt
from gui.component_account_manager.traffic_accounts import TrafficAccountsTab
from gui.component_account_manager.sales_accounts import SalesAccountsTab
from loguru import logger


class AccountManagerTab(QWidget):
    """Главный виджет менеджера аккаунтов с вкладками"""

    def __init__(self):
        super().__init__()
        self.setObjectName("AccountManagerTab")

        # Основной layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Заголовок секции
        self._create_header(layout)

        # Система вкладок
        self._create_tabs(layout)

        logger.debug("AccountManager with tabs initialized")

    def _create_header(self, layout):
        """Создание заголовка секции"""
        header_container = QWidget()
        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(0, 0, 0, 10)

        # Хлебные крошки
        breadcrumb = QLabel("Главная / Менеджер аккаунтов")
        breadcrumb.setObjectName("Breadcrumb")
        breadcrumb.setStyleSheet("""
            QLabel#Breadcrumb {
                font-size: 14px;
                color: rgba(255, 255, 255, 0.6);
                font-weight: 400;
            }
        """)

        header_layout.addWidget(breadcrumb)
        header_layout.addStretch()

        layout.addWidget(header_container)

    def _create_tabs(self, layout):
        """Создание системы вкладок"""
        self.tab_widget = QTabWidget()
        self.tab_widget.setObjectName("AccountTabs")

        # Настройка стилей вкладок
        self.tab_widget.setStyleSheet("""
            QTabWidget#AccountTabs::pane {
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                background: transparent;
                top: -1px;
            }

            QTabBar::tab {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-bottom: none;
                padding: 12px 24px;
                margin: 0 2px;
                border-radius: 8px 8px 0 0;
                color: rgba(255, 255, 255, 0.7);
                font-size: 14px;
                font-weight: 500;
                min-width: 120px;
            }

            QTabBar::tab:selected {
                background: rgba(59, 130, 246, 0.15);
                border: 1px solid rgba(59, 130, 246, 0.3);
                color: #FFFFFF;
                font-weight: 600;
            }

            QTabBar::tab:hover:!selected {
                background: rgba(255, 255, 255, 0.08);
                color: rgba(255, 255, 255, 0.9);
            }
        """)

        # Вкладка для работы с трафиком (всегда доступна)
        self.traffic_tab = TrafficAccountsTab()
        self.tab_widget.addTab(self.traffic_tab, "🚀 Трафик")

        # Вкладка для продаж (проверяем доступ)
        if self._has_sales_access():
            self.sales_tab = SalesAccountsTab()
            self.tab_widget.addTab(self.sales_tab, "💰 Продажи")
        else:
            logger.info("Доступ к модулю продаж заблокирован")

        layout.addWidget(self.tab_widget)

    def _has_sales_access(self) -> bool:
        """
        Проверяет доступ к модулю продаж
        В будущем здесь будет проверка с сервера
        """
        # TODO: Заменить на реальную проверку с сервера
        # user_permissions = get_user_permissions_from_server()
        # return "sales_module" in user_permissions

        # Пока что заглушка - доступ только для организации
        # Измените на True для тестирования
        return True  # Только для вашей организации

    def refresh_permissions(self):
        """Обновляет доступ к вкладкам при изменении разрешений"""
        current_count = self.tab_widget.count()
        has_sales = self._has_sales_access()

        # Если нет доступа к продажам, но вкладка есть - удаляем
        if not has_sales and current_count > 1:
            self.tab_widget.removeTab(1)
            logger.info("Вкладка продаж удалена - нет доступа")

        # Если есть доступ к продажам, но вкладки нет - добавляем
        elif has_sales and current_count == 1:
            self.sales_tab = SalesAccountsTab()
            self.tab_widget.addTab(self.sales_tab, "💰 Продажи")
            logger.info("Вкладка продаж добавлена")


# Функция для тестирования доступа
def test_sales_access(enable_sales: bool):
    """Тестирует включение/выключение доступа к продажам"""
    # Временно меняем метод проверки доступа
    original_method = AccountManagerTab._has_sales_access
    AccountManagerTab._has_sales_access = lambda self: enable_sales

    print(f"Тест: доступ к продажам = {enable_sales}")

    # Восстанавливаем оригинальный метод
    AccountManagerTab._has_sales_access = original_method