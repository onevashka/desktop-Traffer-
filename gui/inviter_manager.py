# gui/inviter_manager.py - ИСПРАВЛЕННАЯ ПОЛНАЯ ВЕРСИЯ
"""
Главный менеджер инвайтера - интерфейс для массовых инвайтов
ИНТЕГРИРОВАН С МОДУЛЕМ src/modules/impl/inviter/
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
    """Главный виджет менеджера инвайтера - ИНТЕГРИРОВАН С МОДУЛЕМ"""

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

        logger.debug("InviterManager GUI инициализирован с интеграцией модуля")

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

        # Кнопка обновления
        self.refresh_btn = QPushButton("🔄 Обновить")
        self.refresh_btn.setObjectName("RefreshButton")
        self.refresh_btn.setFixedSize(120, 40)
        self.refresh_btn.setStyleSheet("""
            QPushButton#RefreshButton {
                background: rgba(255, 255, 255, 0.06);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 8px;
                color: rgba(255, 255, 255, 0.9);
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton#RefreshButton:hover {
                background: rgba(255, 255, 255, 0.12);
                border: 1px solid rgba(59, 130, 246, 0.5);
                color: #FFFFFF;
            }
        """)
        self.refresh_btn.clicked.connect(self._on_refresh_profiles)

        buttons_layout.addWidget(self.create_profile_btn)
        buttons_layout.addWidget(self.start_all_btn)
        buttons_layout.addWidget(self.stop_all_btn)
        buttons_layout.addWidget(self.refresh_btn)

        return buttons_layout

    def _on_create_profile(self):
        """Обработка создания нового профиля - ИСПОЛЬЗУЕТ МОДУЛЬ"""
        try:
            from gui.notifications import show_success, show_error, show_info
            from src.modules.impl.inviter import create_profile

            # Показываем диалог создания профиля
            profile_data = show_create_profile_dialog(self)

            if profile_data and profile_data.get('name'):
                profile_name = profile_data['name']

                show_info(
                    "Создание профиля",
                    f"Создаем профиль '{profile_name}'..."
                )

                # ИНТЕГРАЦИЯ: Создаем профиль через модуль
                result = create_profile(profile_name, profile_data)

                if result.get('success'):
                    # Перезагружаем интерфейс
                    self._reload_all_data()

                    show_success(
                        "Профиль создан",
                        f"✅ Профиль '{profile_name}' успешно создан\n"
                        f"📁 Структура папок создана\n"
                        f"📝 Конфигурация сохранена\n"
                        f"📋 Базы данных инициализированы"
                    )

                    logger.info(f"✅ Профиль создан через GUI модуль: {profile_name}")
                else:
                    show_error(
                        "Ошибка создания",
                        f"❌ {result.get('message', 'Неизвестная ошибка')}"
                    )

        except Exception as e:
            logger.error(f"❌ Ошибка создания профиля через GUI: {e}")
            from gui.notifications import show_error
            show_error("Критическая ошибка", f"Не удалось создать профиль: {e}")

    def _on_start_all_profiles(self):
        """Запускает все профили - ИСПОЛЬЗУЕТ МОДУЛЬ"""
        try:
            from src.modules.impl.inviter import start_all_profiles
            from gui.notifications import show_success, show_info, show_error, show_warning

            show_info("Массовый запуск", "Запускаем все профили...")

            # ИНТЕГРАЦИЯ: Запускаем через модуль
            results = start_all_profiles()

            success_count = sum(1 for success in results.values() if success)
            total_count = len(results)

            if success_count > 0:
                # Обновляем интерфейс
                self._reload_all_data()

                if success_count == total_count:
                    show_success(
                        "Все профили запущены",
                        f"✅ Успешно запущено: {success_count} профилей"
                    )
                else:
                    show_warning(
                        "Частичный запуск",
                        f"⚠️ Запущено: {success_count}/{total_count} профилей"
                    )
            else:
                show_error(
                    "Ошибка запуска",
                    "❌ Не удалось запустить ни одного профиля"
                )

            logger.info(f"🚀 Массовый запуск через GUI модуль: {success_count}/{total_count}")

        except Exception as e:
            logger.error(f"❌ Ошибка массового запуска через GUI: {e}")
            from gui.notifications import show_error
            show_error("Критическая ошибка", f"Ошибка массового запуска: {e}")

    def _on_stop_all_profiles(self):
        """Останавливает все профили - ИСПОЛЬЗУЕТ МОДУЛЬ"""
        try:
            from src.modules.impl.inviter import stop_all_profiles
            from gui.notifications import show_warning, show_info, show_error

            show_info("Массовая остановка", "Останавливаем все профили...")

            # ИНТЕГРАЦИЯ: Останавливаем через модуль
            results = stop_all_profiles()

            success_count = sum(1 for success in results.values() if success)
            total_count = len(results)

            if success_count > 0:
                # Обновляем интерфейс
                self._reload_all_data()

                show_warning(
                    "Профили остановлены",
                    f"⏸️ Остановлено: {success_count}/{total_count} профилей"
                )
            else:
                show_info(
                    "Остановка завершена",
                    "Все профили уже были остановлены"
                )

            logger.info(f"⏸️ Массовая остановка через GUI модуль: {success_count}/{total_count}")

        except Exception as e:
            logger.error(f"❌ Ошибка массовой остановки через GUI: {e}")

    def _on_refresh_profiles(self):
        """Обновляет профили - ИСПОЛЬЗУЕТ МОДУЛЬ"""
        try:
            from src.modules.impl.inviter import refresh_inviter_module
            from gui.notifications import show_success, show_info

            show_info("Обновление", "Перезагружаем модуль инвайтера...")

            # ИНТЕГРАЦИЯ: Обновляем через модуль
            refresh_inviter_module()

            # Перезагружаем интерфейс
            self._reload_all_data()

            show_success(
                "Обновление завершено",
                "✅ Модуль инвайтера перезагружен"
            )

            logger.info("🔄 Модуль инвайтера обновлен через GUI")

        except Exception as e:
            logger.error(f"❌ Ошибка обновления через GUI: {e}")
            from gui.notifications import show_error
            show_error("Ошибка обновления", f"Не удалось обновить модуль: {e}")

    def _create_stats_section(self, layout):
        """Создает секцию статистики - ИСПОЛЬЗУЕТ РЕАЛЬНЫЕ ДАННЫЕ ИЗ МОДУЛЯ"""
        try:
            from src.modules.impl.inviter import get_inviter_stats

            # Получаем реальную статистику из модуля
            stats_data = get_inviter_stats()

            self.stats_widget = InviterStatsWidget(stats_data)
            layout.addWidget(self.stats_widget)

            logger.debug("📊 Статистика инвайтера загружена из модуля")

        except Exception as e:
            logger.error(f"❌ Ошибка загрузки статистики из модуля: {e}")

            # Fallback на заглушку
            mock_stats = [
                ("Модуль загружается", "...", "#F59E0B", "loading"),
                ("Ошибка загрузки", "0", "#EF4444", "error")
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

        # Таблица профилей - ЗАГРУЖАЕТ ДАННЫЕ ИЗ МОДУЛЯ
        self.profiles_table = InviterTableWidget()
        self._load_profiles_from_module()
        layout.addWidget(self.profiles_table)

    def _load_profiles_from_module(self):
        """Загружает реальные данные профилей из модуля"""
        try:
            from src.modules.impl.inviter import get_all_profiles_for_gui

            # Получаем реальные профили из модуля
            profiles_data = get_all_profiles_for_gui()

            logger.debug(f"📨 Загружено профилей из модуля: {len(profiles_data)}")

            # Очищаем таблицу и загружаем новые данные
            if hasattr(self.profiles_table, 'clear_profiles'):
                self.profiles_table.clear_profiles()

            # Загружаем профили в таблицу
            for profile_data in profiles_data:
                self.profiles_table.add_profile(profile_data)

        except Exception as e:
            logger.error(f"❌ Ошибка загрузки профилей из модуля: {e}")

            # Показываем ошибку в интерфейсе
            try:
                from gui.notifications import show_error
                show_error(
                    "Ошибка загрузки",
                    f"Не удалось загрузить профили из модуля: {e}"
                )
            except:
                pass

    def _reload_stats_from_module(self):
        """Перезагружает статистику из модуля"""
        try:
            from src.modules.impl.inviter import get_inviter_stats

            # Получаем новую статистику из модуля
            new_stats = get_inviter_stats()

            # Обновляем каждый элемент статистики
            for i, (title, value, color, key) in enumerate(new_stats):
                if i < len(self.stats_widget.stat_boxes):
                    self.stats_widget.update_stat(i, value)

            logger.debug("📊 Статистика обновлена из модуля")

        except Exception as e:
            logger.error(f"❌ Ошибка обновления статистики из модуля: {e}")

    def _reload_all_data(self):
        """Перезагружает все данные из модуля"""
        try:
            logger.debug("🔄 Перезагружаем все данные из модуля...")

            # Обновляем статистику
            self._reload_stats_from_module()

            # Обновляем таблицу профилей
            self._load_profiles_from_module()

            logger.debug("✅ Все данные обновлены из модуля")

        except Exception as e:
            logger.error(f"❌ Ошибка перезагрузки данных из модуля: {e}")

    def refresh_data(self):
        """
        Основной метод обновления данных - ВЫЗЫВАЕТСЯ ИЗВНЕ
        ПОЛНОСТЬЮ ИНТЕГРИРОВАН С МОДУЛЕМ
        """
        try:
            logger.info("🔄 Обновляем данные GUI инвайтера из модуля...")

            # Перезагружаем все данные из модуля
            self._reload_all_data()

            logger.info("✅ Данные GUI инвайтера обновлены из модуля")

        except Exception as e:
            logger.error(f"❌ Ошибка обновления данных GUI инвайтера: {e}")

    def start_animation(self):
        """Запускает анимацию появления"""
        try:
            # Анимация статистики
            if hasattr(self, 'stats_widget'):
                QTimer.singleShot(100, self.stats_widget.animate_appearance)

            # Анимация таблицы
            if hasattr(self, 'profiles_table'):
                QTimer.singleShot(300, self.profiles_table.animate_appearance)

            logger.debug("🎬 Анимации GUI инвайтера запущены")

        except Exception as e:
            logger.error(f"❌ Ошибка запуска анимаций: {e}")

    def get_module_status(self) -> dict:
        """Получает статус модуля для диагностики"""
        try:
            from src.modules.impl.inviter.inviter_manager import _inviter_module_manager

            if _inviter_module_manager:
                return {
                    'module_loaded': True,
                    'profiles_count': len(_inviter_module_manager.profile_manager.profiles),
                    'active_processes': len(_inviter_module_manager.active_processes),
                    'stats_cache': _inviter_module_manager._stats_cache
                }
            else:
                return {
                    'module_loaded': False,
                    'error': 'Модуль не инициализирован'
                }

        except Exception as e:
            return {
                'module_loaded': False,
                'error': str(e)
            }

    def show_module_diagnostics(self):
        """Показывает диагностику модуля (для отладки)"""
        try:
            from gui.notifications import show_info

            status = self.get_module_status()

            if status.get('module_loaded'):
                show_info(
                    "Диагностика модуля",
                    f"✅ Модуль загружен\n"
                    f"📨 Профилей: {status.get('profiles_count', 0)}\n"
                    f"🚀 Активных процессов: {status.get('active_processes', 0)}"
                )
            else:
                show_info(
                    "Диагностика модуля",
                    f"❌ Модуль не загружен\n"
                    f"Ошибка: {status.get('error', 'Неизвестная ошибка')}"
                )

        except Exception as e:
            logger.error(f"❌ Ошибка диагностики модуля: {e}")

    def __del__(self):
        """Деструктор - останавливаем все процессы при закрытии"""
        try:
            # При закрытии GUI останавливаем все процессы
            from src.modules.impl.inviter import stop_all_profiles
            stop_all_profiles()
            logger.debug("🔄 GUI инвайтера закрыт, процессы остановлены")
        except:
            pass  # Игнорируем ошибки при закрытии