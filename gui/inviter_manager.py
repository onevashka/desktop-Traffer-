# gui/inviter_manager.py - ИСПРАВЛЕННАЯ ВЕРСИЯ
"""
Главный менеджер инвайтера - интерфейс для массовых инвайтов
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QScrollArea, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer
from gui.component_inviter.inviter_table import InviterTableWidget
from gui.component_inviter.inviter_stats import InviterStatsWidget
from gui.dialogs.inviter_dialogs import show_create_profile_dialog
from loguru import logger


class InviterManagerTab(QWidget):
    """Главный виджет менеджера инвайтера"""

    def __init__(self):
        super().__init__()
        self.setObjectName("InviterManagerTab")

        # Основной layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Создаем заголовок
        self._create_header(layout)

        # Статистика инвайтера
        self._create_stats_section(layout)

        # Основная таблица профилей
        self._create_profiles_section(layout)

        logger.debug("InviterManager initialized")

    def _create_header(self, layout):
        """Создание заголовка секции"""
        header_container = QWidget()
        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(0, 0, 0, 10)

        # Хлебные крошки
        breadcrumb = QLabel("Главная / Инвайтер")
        breadcrumb.setObjectName("Breadcrumb")
        breadcrumb.setStyleSheet("""
            QLabel#Breadcrumb {
                font-size: 14px;
                color: rgba(255, 255, 255, 0.6);
                font-weight: 400;
            }
        """)

        # Кнопки управления
        control_buttons = self._create_control_buttons()

        header_layout.addWidget(breadcrumb)
        header_layout.addStretch()
        header_layout.addLayout(control_buttons)

        layout.addWidget(header_container)

    def _create_control_buttons(self):
        """Создает кнопки управления инвайтером"""
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)

        # Кнопка создания профиля
        self.create_profile_btn = QPushButton("+ Создать профиль")
        self.create_profile_btn.setObjectName("CreateProfileButton")
        self.create_profile_btn.setFixedSize(150, 40)
        self.create_profile_btn.setStyleSheet("""
            QPushButton#CreateProfileButton {
                background: #10B981;
                border: 1px solid #059669;
                border-radius: 8px;
                color: #FFFFFF;
                font-size: 14px;
                font-weight: 600;
            }
            QPushButton#CreateProfileButton:hover {
                background: #059669;
                border-color: #047857;
            }
            QPushButton#CreateProfileButton:pressed {
                background: #047857;
            }
        """)

        # ИСПРАВЛЕНО: Подключаем обработчик ПОСЛЕ создания кнопки
        self.create_profile_btn.clicked.connect(self._on_create_profile)

        # Кнопка запуска всех
        self.start_all_btn = QPushButton("▶️ Запустить все")
        self.start_all_btn.setObjectName("StartAllButton")
        self.start_all_btn.setFixedSize(140, 40)
        self.start_all_btn.setStyleSheet("""
            QPushButton#StartAllButton {
                background: #3B82F6;
                border: 1px solid #2563EB;
                border-radius: 8px;
                color: #FFFFFF;
                font-size: 14px;
                font-weight: 600;
            }
            QPushButton#StartAllButton:hover {
                background: #2563EB;
                border-color: #1D4ED8;
            }
        """)
        self.start_all_btn.clicked.connect(self._on_start_all_profiles)

        # Кнопка остановки всех
        self.stop_all_btn = QPushButton("⏸️ Остановить все")
        self.stop_all_btn.setObjectName("StopAllButton")
        self.stop_all_btn.setFixedSize(150, 40)
        self.stop_all_btn.setStyleSheet("""
            QPushButton#StopAllButton {
                background: #EF4444;
                border: 1px solid #DC2626;
                border-radius: 8px;
                color: #FFFFFF;
                font-size: 14px;
                font-weight: 600;
            }
            QPushButton#StopAllButton:hover {
                background: #DC2626;
                border-color: #B91C1C;
            }
        """)
        self.stop_all_btn.clicked.connect(self._on_stop_all_profiles)

        buttons_layout.addWidget(self.create_profile_btn)
        buttons_layout.addWidget(self.start_all_btn)
        buttons_layout.addWidget(self.stop_all_btn)

        return buttons_layout

    def _on_create_profile(self):
        """Обработка создания нового профиля"""
        try:
            from gui.notifications import show_success, show_error

            # Показываем диалог создания профиля
            profile_data = show_create_profile_dialog(self)

            if profile_data:
                # Добавляем профиль в таблицу
                self.profiles_table.add_profile(profile_data)

                show_success(
                    "Профиль создан",
                    f"Профиль '{profile_data['name']}' успешно создан"
                )

                logger.info(f"✅ Создан новый профиль: {profile_data['name']}")

        except Exception as e:
            logger.error(f"❌ Ошибка создания профиля: {e}")
            from gui.notifications import show_error
            show_error("Ошибка", f"Не удалось создать профиль: {e}")

    def _on_start_all_profiles(self):
        """Запускает все профили"""
        try:
            if hasattr(self, 'profiles_table'):
                self.profiles_table.start_all_profiles()

                from gui.notifications import show_success
                show_success(
                    "Профили запущены",
                    "Все профили инвайтера запущены"
                )
                logger.info("🚀 Все профили инвайтера запущены")
        except Exception as e:
            logger.error(f"❌ Ошибка запуска всех профилей: {e}")

    def _on_stop_all_profiles(self):
        """Останавливает все профили"""
        try:
            if hasattr(self, 'profiles_table'):
                self.profiles_table.stop_all_profiles()

                from gui.notifications import show_warning
                show_warning(
                    "Профили остановлены",
                    "Все профили инвайтера остановлены"
                )
                logger.info("⏸️ Все профили инвайтера остановлены")
        except Exception as e:
            logger.error(f"❌ Ошибка остановки всех профилей: {e}")

    def _create_stats_section(self, layout):
        """Создает секцию статистики"""
        # Заглушка статистики (потом заменим на реальную)
        mock_stats = [
            ("Активных профилей", "3", "#10B981", "active"),
            ("Всего инвайтов", "1,247", "#3B82F6", "total_invites"),
            ("Успешных инвайтов", "923", "#059669", "success_invites"),
            ("Заблокированных", "12", "#EF4444", "blocked"),
            ("В ожидании", "45", "#F59E0B", "pending")
        ]

        self.stats_widget = InviterStatsWidget(mock_stats)
        layout.addWidget(self.stats_widget)

    def _create_profiles_section(self, layout):
        """Создает секцию с таблицей профилей"""
        # Заголовок секции
        section_header = QWidget()
        section_layout = QHBoxLayout(section_header)
        section_layout.setContentsMargins(0, 0, 0, 0)

        section_title = QLabel("📨 Профили инвайтера")
        section_title.setObjectName("SectionTitle")
        section_title.setStyleSheet("""
            QLabel#SectionTitle {
                font-size: 18px;
                font-weight: 600;
                color: rgba(255, 255, 255, 0.9);
                margin: 10px 0;
            }
        """)

        section_layout.addWidget(section_title)
        section_layout.addStretch()

        layout.addWidget(section_header)

        # Таблица профилей
        self.profiles_table = InviterTableWidget()
        layout.addWidget(self.profiles_table)

    def refresh_data(self):
        """Обновляет данные инвайтера"""
        try:
            logger.info("🔄 Обновляем данные инвайтера...")

            # Обновляем статистику
            if hasattr(self, 'stats_widget'):
                # TODO: получить реальную статистику
                pass

            # Обновляем таблицу профилей
            if hasattr(self, 'profiles_table'):
                self.profiles_table.refresh_data()

            logger.info("✅ Данные инвайтера обновлены")

        except Exception as e:
            logger.error(f"❌ Ошибка обновления данных инвайтера: {e}")

    def start_animation(self):
        """Запускает анимацию появления"""
        # Анимация статистики
        if hasattr(self, 'stats_widget'):
            QTimer.singleShot(100, self.stats_widget.animate_appearance)

        # Анимация таблицы
        if hasattr(self, 'profiles_table'):
            QTimer.singleShot(300, self.profiles_table.animate_appearance)