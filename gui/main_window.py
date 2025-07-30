# desktop-Traffer/gui/main_window.py
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QLabel, QFrame, QStackedWidget, QSizePolicy
)
from PySide6.QtCore import Qt, QPropertyAnimation, QRect, QEasingCurve, QTimer
from PySide6.QtGui import QFont, QIcon
from gui.account_manager import AccountManagerTab
from gui.inviter_manager import InviterManagerTab
from log_config import logger


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("desktop-Traffer")
        self.resize(1400, 900)
        self.setMinimumSize(1200, 800)

        # Центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Основной layout - горизонтальный
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Создаем сайдбар и основную область
        self._create_sidebar()
        self._create_main_area()

        # Добавляем в layout
        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(self.main_area)

        # Устанавливаем первую вкладку активной
        self._switch_to_accounts()

        logger.debug("MainWindow with sidebar initialized")

        # ВАЖНО: Инициализируем уведомления ПОСЛЕ полного создания окна
        QTimer.singleShot(100, self._init_notifications)

    def _init_notifications(self):
        """Инициализирует систему уведомлений после создания окна"""
        try:
            from gui.notifications import init_notification_manager
            self.notification_manager = init_notification_manager(self)
            logger.debug("✅ Система уведомлений инициализирована")

            # Показываем приветственное уведомление
            QTimer.singleShot(500, self.show_app_ready_notification)

        except Exception as e:
            logger.error(f"❌ Ошибка инициализации уведомлений: {e}")

    def show_app_ready_notification(self):
        """Показывает уведомление о готовности приложения"""
        try:
            from gui.notifications import show_success
            show_success(
                "Приложение готово",
                "desktop-Traffer успешно запущен!"
            )
        except Exception as e:
            logger.error(f"❌ Ошибка показа уведомления: {e}")

    def show_navigation_info(self, section_name: str):
        """Показывает информацию о переключении разделов"""
        try:
            from gui.notifications import show_info

            if section_name == "accounts":
                show_info(
                    "Менеджер аккаунтов",
                    "Управление Telegram аккаунтами"
                )
            elif section_name == "inviter":
                show_info(
                    "Инвайтер",
                    "Массовые инвайты в чаты и каналы"
                )
            elif section_name == "modules":
                show_info(
                    "Модули автоматизации",
                    "Раздел находится в разработке"
                )
        except Exception as e:
            logger.error(f"❌ Ошибка показа навигационного уведомления: {e}")

    def _create_sidebar(self):
        """Создание левого сайдбара"""
        self.sidebar = QFrame()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setFixedWidth(280)
        self.sidebar.setStyleSheet("""
            QFrame#Sidebar {
                background: rgba(255, 255, 255, 0.03);
                border-right: 1px solid rgba(255, 255, 255, 0.1);
            }
        """)

        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        # Логотип/заголовок
        header = self._create_sidebar_header()
        sidebar_layout.addWidget(header)

        # Навигационные кнопки
        nav_section = self._create_navigation()
        sidebar_layout.addWidget(nav_section)

        # Растягиваем оставшееся пространство
        sidebar_layout.addStretch()

        # Футер с версией
        footer = self._create_sidebar_footer()
        sidebar_layout.addWidget(footer)

    def _create_sidebar_header(self):
        """Заголовок сайдбара"""
        header = QWidget()
        header.setObjectName("SidebarHeader")
        header.setFixedHeight(80)
        header.setStyleSheet("""
            QWidget#SidebarHeader {
                background: rgba(59, 130, 246, 0.1);
                border-bottom: 1px solid rgba(59, 130, 246, 0.2);
            }
        """)

        layout = QVBoxLayout(header)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(5)

        # Логотип
        logo = QLabel("📱 TeleCRM")
        logo.setObjectName("Logo")
        logo.setStyleSheet("""
            QLabel#Logo {
                font-size: 20px;
                font-weight: 700;
                color: #3B82F6;
            }
        """)

        # Подзаголовок
        subtitle = QLabel("Telegram Automation")
        subtitle.setObjectName("Subtitle")
        subtitle.setStyleSheet("""
            QLabel#Subtitle {
                font-size: 12px;
                color: rgba(255, 255, 255, 0.6);
                font-weight: 400;
            }
        """)

        layout.addWidget(logo)
        layout.addWidget(subtitle)

        return header

    def _create_navigation(self):
        """Навигационные кнопки"""
        nav_widget = QWidget()
        layout = QVBoxLayout(nav_widget)
        layout.setContentsMargins(15, 20, 15, 0)
        layout.setSpacing(8)

        # Кнопки навигации
        nav_buttons = [
            ("👥", "Менеджер аккаунтов", "accounts", True),
            ("📨", "Инвайтер", "inviter", False),  # НОВАЯ КНОПКА
            ("🏭", "Модули автоматизации", "modules", False),
            ("📊", "Аналитика", "analytics", False),
            ("⚙️", "Настройки", "settings", False),
            ("📋", "Логи", "logs", False),
        ]

        self.nav_buttons = {}
        for icon, text, key, is_active in nav_buttons:
            btn = self._create_nav_button(icon, text, key, is_active)
            self.nav_buttons[key] = btn
            layout.addWidget(btn)

        return nav_widget

    def _create_nav_button(self, icon, text, key, is_active=False):
        """Создание кнопки навигации"""
        btn = QPushButton()
        btn.setObjectName("NavButton")
        btn.setFixedHeight(50)
        btn.setCursor(Qt.PointingHandCursor)

        # Создаем layout для иконки и текста
        btn_widget = QWidget()
        btn_layout = QHBoxLayout(btn_widget)
        btn_layout.setContentsMargins(15, 0, 15, 0)
        btn_layout.setSpacing(12)

        # Иконка
        icon_label = QLabel(icon)
        icon_label.setStyleSheet("font-size: 18px;")
        icon_label.setFixedWidth(24)

        # Текст
        text_label = QLabel(text)
        text_label.setStyleSheet("""
            font-size: 14px;
            font-weight: 500;
            color: rgba(255, 255, 255, 0.8);
        """)

        btn_layout.addWidget(icon_label)
        btn_layout.addWidget(text_label)
        btn_layout.addStretch()

        # Стиль кнопки
        if is_active:
            btn.setStyleSheet("""
                QPushButton#NavButton {
                    background: rgba(59, 130, 246, 0.15);
                    border: none;
                    border-radius: 8px;
                    border-left: 3px solid #3B82F6;
                }
            """)
        else:
            btn.setStyleSheet("""
                QPushButton#NavButton {
                    background: transparent;
                    border: none;
                    border-radius: 8px;
                }
                QPushButton#NavButton:hover {
                    background: rgba(255, 255, 255, 0.05);
                }
                QPushButton#NavButton:pressed {
                    background: rgba(255, 255, 255, 0.1);
                }
            """)

        # Устанавливаем виджет как layout кнопки
        btn_layout_main = QHBoxLayout(btn)
        btn_layout_main.setContentsMargins(0, 0, 0, 0)
        btn_layout_main.addWidget(btn_widget)

        # Подключаем обработчик
        if key == "accounts":
            btn.clicked.connect(self._switch_to_accounts)
        elif key == "modules":
            btn.clicked.connect(self._switch_to_modules)
        elif key == "inviter":
            btn.clicked.connect(self._switch_to_inviter)
        # Добавьте другие обработчики по мере необходимости

        return btn

    def _create_sidebar_footer(self):
        """Футер сайдбара"""
        footer = QWidget()
        footer.setFixedHeight(60)
        footer.setStyleSheet("""
            border-top: 1px solid rgba(255, 255, 255, 0.1);
        """)

        layout = QVBoxLayout(footer)
        layout.setContentsMargins(20, 15, 20, 15)

        version_label = QLabel("v0.1.0 Beta")
        version_label.setStyleSheet("""
            font-size: 11px;
            color: rgba(255, 255, 255, 0.4);
            font-weight: 400;
        """)
        version_label.setAlignment(Qt.AlignCenter)

        layout.addWidget(version_label)

        return footer

    def _create_main_area(self):
        """Создание основной рабочей области"""
        self.main_area = QFrame()
        self.main_area.setObjectName("MainArea")
        self.main_area.setStyleSheet("""
            QFrame#MainArea {
                background: transparent;
            }
        """)

        # StackedWidget для переключения между разными разделами
        self.stacked_widget = QStackedWidget()

        # Добавляем страницы
        self.account_tab = AccountManagerTab()
        self.stacked_widget.addWidget(self.account_tab)

        self.inviter_tab = InviterManagerTab()
        self.stacked_widget.addWidget(self.inviter_tab)

        # Заглушки для других разделов
        self.modules_tab = self._create_placeholder("🏭 Модули автоматизации", "Здесь будут модули для автоматизации")
        self.stacked_widget.addWidget(self.modules_tab)

        # Layout для основной области
        main_area_layout = QVBoxLayout(self.main_area)
        main_area_layout.setContentsMargins(0, 0, 0, 0)
        main_area_layout.addWidget(self.stacked_widget)

    def _create_placeholder(self, title, description):
        """Создание заглушки для разделов"""
        placeholder = QWidget()
        layout = QVBoxLayout(placeholder)
        layout.setAlignment(Qt.AlignCenter)

        title_label = QLabel(title)
        title_label.setStyleSheet("""
            font-size: 24px;
            font-weight: 600;
            color: rgba(255, 255, 255, 0.8);
            margin-bottom: 10px;
        """)
        title_label.setAlignment(Qt.AlignCenter)

        desc_label = QLabel(description)
        desc_label.setStyleSheet("""
            font-size: 16px;
            color: rgba(255, 255, 255, 0.5);
        """)
        desc_label.setAlignment(Qt.AlignCenter)

        layout.addWidget(title_label)
        layout.addWidget(desc_label)

        return placeholder

    def _switch_to_accounts(self):
        """Переключение на менеджер аккаунтов"""
        self.stacked_widget.setCurrentIndex(0)
        self._update_nav_buttons("accounts")

        # Показываем информацию только при первом переходе
        if not hasattr(self, '_accounts_visited'):
            self._accounts_visited = True
            QTimer.singleShot(300, lambda: self.show_navigation_info("accounts"))

    def _switch_to_inviter(self):
        """Переключение на инвайтер"""
        self.stacked_widget.setCurrentIndex(1)
        self._update_nav_buttons("inviter")

        # Запускаем анимацию появления
        if hasattr(self.inviter_tab, 'start_animation'):
            QTimer.singleShot(100, self.inviter_tab.start_animation)

        QTimer.singleShot(300, lambda: self.show_navigation_info("inviter"))

    def _switch_to_modules(self):
        """Переключение на модули"""
        self.stacked_widget.setCurrentIndex(2)
        self._update_nav_buttons("modules")
        QTimer.singleShot(300, lambda: self.show_navigation_info("modules"))

    def _update_nav_buttons(self, active_key):
        """Обновление стилей навигационных кнопок"""
        for key, btn in self.nav_buttons.items():
            if key == active_key:
                btn.setStyleSheet("""
                    QPushButton#NavButton {
                        background: rgba(59, 130, 246, 0.15);
                        border: none;
                        border-radius: 8px;
                        border-left: 3px solid #3B82F6;
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton#NavButton {
                        background: transparent;
                        border: none;
                        border-radius: 8px;
                    }
                    QPushButton#NavButton:hover {
                        background: rgba(255, 255, 255, 0.05);
                    }
                    QPushButton#NavButton:pressed {
                        background: rgba(255, 255, 255, 0.1);
                    }
                """)

    # Методы для тестирования уведомлений
    def test_notifications(self):
        """Тестирует все типы уведомлений"""
        try:
            from gui.notifications import show_success, show_error, show_warning, show_info

            show_info("Тест 1", "Информационное уведомление")
            QTimer.singleShot(1000, lambda: show_success("Тест 2", "Успешное выполнение"))
            QTimer.singleShot(2000, lambda: show_warning("Тест 3", "Предупреждение"))
            QTimer.singleShot(3000, lambda: show_error("Тест 4", "Ошибка системы"))
        except Exception as e:
            logger.error(f"❌ Ошибка тестирования уведомлений: {e}")

    def _clear_notifications(self):
        """Очищает все уведомления"""
        try:
            if hasattr(self, 'notification_manager'):
                self.notification_manager.clear_all()
                from gui.notifications import show_info
                show_info("Система", "Все уведомления очищены")
        except Exception as e:
            logger.error(f"❌ Ошибка очистки уведомлений: {e}")

    # Обработка событий окна
    def resizeEvent(self, event):
        """Обработка изменения размера окна"""
        super().resizeEvent(event)
        # Уведомления автоматически обновят позицию через eventFilter

    def moveEvent(self, event):
        """Обработка перемещения окна"""
        super().moveEvent(event)
        # Уведомления автоматически обновят позицию через eventFilter