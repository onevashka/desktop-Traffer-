# gui/inviter_manager_optimized.py - ОПТИМИЗИРОВАННАЯ ВЕРСИЯ МЕНЕДЖЕРА
"""
ОПТИМИЗИРОВАННЫЙ главный менеджер инвайтера - НЕ БЛОКИРУЕТ GUI при больших нагрузках
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
)
from PySide6.QtCore import QTimer, QThread, Signal
from gui.component_inviter.inviter_table_optimized import OptimizedInviterTableWidget
from gui.component_inviter.inviter_stats import InviterStatsWidget
from gui.dialogs.inviter_dialogs import show_create_profile_dialog
from loguru import logger
import threading
from paths import Path


class OptimizedInviterManagerTab(QWidget):
    """ОПТИМИЗИРОВАННЫЙ главный виджет менеджера инвайтера"""

    def __init__(self):
        super().__init__()
        self.setObjectName("InviterManagerTab")

        # Флаги состояния
        self.is_mass_operation_running = False
        self.pending_operations = []

        # Основной layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Создаем заголовок
        self._create_header(layout)

        # Статистика инвайтера
        self._create_stats_section(layout)

        # ОПТИМИЗИРОВАННАЯ основная таблица профилей
        self._create_profiles_section(layout)

        # ИНИЦИАЛИЗИРУЕМ ФОНОВЫЕ РАБОЧИЕ
        self._init_background_workers()

        logger.debug("ОПТИМИЗИРОВАННЫЙ InviterManager GUI инициализирован")

    def _init_background_workers(self):
        """Инициализирует систему фоновых рабочих"""
        try:
            from gui.workers.background_workers import get_worker_manager

            self.worker_manager = get_worker_manager()
            if not self.worker_manager.is_initialized:
                self.worker_manager.initialize()

            logger.info("✅ Фоновые рабочие потоки инициализированы для InviterManager")

        except Exception as e:
            logger.error(f"❌ Ошибка инициализации фоновых рабочих: {e}")

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
        """Создает ОПТИМИЗИРОВАННЫЕ кнопки управления"""
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

        # ОПТИМИЗИРОВАННАЯ кнопка запуска всех
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
        self.start_all_btn.clicked.connect(self._on_start_all_profiles_optimized)

        # ОПТИМИЗИРОВАННАЯ кнопка остановки всех
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
        self.stop_all_btn.clicked.connect(self._on_stop_all_profiles_optimized)

        # Кнопка генерации отчета
        self.report_btn = QPushButton("📊 Отчет по аккаунтам")
        self.report_btn.setObjectName("ReportButton")
        self.report_btn.setFixedSize(170, 40)
        self.report_btn.setStyleSheet("""
            QPushButton#ReportButton {
                background: #8B5CF6;
                border: 1px solid #7C3AED;
                border-radius: 8px;
                color: #FFFFFF;
                font-size: 14px;
                font-weight: 600;
            }
            QPushButton#ReportButton:hover {
                background: #7C3AED;
                border-color: #6D28D9;
            }
            QPushButton#ReportButton:pressed {
                background: #6D28D9;
            }
        """)
        self.report_btn.clicked.connect(self._on_generate_accounts_report)

        # ОПТИМИЗИРОВАННАЯ кнопка обновления
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
        self.refresh_btn.clicked.connect(self._on_refresh_profiles_optimized)

        buttons_layout.addWidget(self.create_profile_btn)
        buttons_layout.addWidget(self.start_all_btn)
        buttons_layout.addWidget(self.stop_all_btn)
        buttons_layout.addWidget(self.report_btn)
        buttons_layout.addWidget(self.refresh_btn)

        return buttons_layout

    def _on_create_profile(self):
        """ОПТИМИЗИРОВАННОЕ создание нового профиля"""
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

                # АСИНХРОННОЕ создание профиля
                def create_task():
                    try:
                        result = create_profile(profile_name, profile_data)

                        # Обновляем GUI в главном потоке
                        QTimer.singleShot(100, lambda: self._on_profile_created(result, profile_name))

                    except Exception as e:
                        logger.error(f"❌ Ошибка создания профиля: {e}")
                        QTimer.singleShot(100, lambda: self._on_profile_create_error(str(e)))

                # Запускаем в фоне
                thread = threading.Thread(target=create_task, daemon=True)
                thread.start()

        except Exception as e:
            logger.error(f"❌ Ошибка создания профиля через GUI: {e}")
            from gui.notifications import show_error
            show_error("Критическая ошибка", f"Не удалось создать профиль: {e}")

    def _on_profile_created(self, result, profile_name):
        """Обработка успешного создания профиля"""
        from gui.notifications import show_success, show_error

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

    def _on_profile_create_error(self, error_message):
        """Обработка ошибки создания профиля"""
        from gui.notifications import show_error
        show_error("Ошибка создания", f"❌ {error_message}")

    def _on_start_all_profiles_optimized(self):
        """ОПТИМИЗИРОВАННЫЙ запуск всех профилей - НЕ БЛОКИРУЕТ GUI"""
        if self.is_mass_operation_running:
            logger.warning("⚠️ Массовая операция уже выполняется")
            return

        try:
            from gui.notifications import show_info

            self.is_mass_operation_running = True
            self._set_mass_operation_buttons_state(False)

            show_info("Массовый запуск", "Запускаем все профили в фоне...")

            # АСИНХРОННЫЙ запуск всех профилей
            def start_all_task():
                try:
                    from src.modules.impl.inviter import start_all_profiles

                    results = start_all_profiles()

                    # Обновляем GUI в главном потоке
                    QTimer.singleShot(100, lambda: self._on_start_all_completed(results))

                except Exception as e:
                    logger.error(f"❌ Ошибка массового запуска: {e}")
                    QTimer.singleShot(100, lambda: self._on_mass_operation_error("запуска", str(e)))

            # Запускаем в фоне
            thread = threading.Thread(target=start_all_task, daemon=True)
            thread.start()

        except Exception as e:
            logger.error(f"❌ Ошибка массового запуска через GUI: {e}")
            self._on_mass_operation_error("запуска", str(e))

    def _on_start_all_completed(self, results):
        """Обработка завершения массового запуска"""
        from gui.notifications import show_success, show_warning, show_error

        self.is_mass_operation_running = False
        self._set_mass_operation_buttons_state(True)

        success_count = sum(1 for success in results.values() if success)
        total_count = len(results)

        if success_count > 0:
            # Перезагружаем интерфейс
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

    def _on_stop_all_profiles_optimized(self):
        """ОПТИМИЗИРОВАННАЯ остановка всех профилей - НЕ БЛОКИРУЕТ GUI"""
        if self.is_mass_operation_running:
            logger.warning("⚠️ Массовая операция уже выполняется")
            return

        try:
            from gui.notifications import show_info

            self.is_mass_operation_running = True
            self._set_mass_operation_buttons_state(False)

            show_info("Массовая остановка", "Останавливаем все профили в фоне...")

            # АСИНХРОННАЯ остановка всех профилей
            def stop_all_task():
                try:
                    from src.modules.impl.inviter import stop_all_profiles

                    results = stop_all_profiles()

                    # Обновляем GUI в главном потоке
                    QTimer.singleShot(100, lambda: self._on_stop_all_completed(results))

                except Exception as e:
                    logger.error(f"❌ Ошибка массовой остановки: {e}")
                    QTimer.singleShot(100, lambda: self._on_mass_operation_error("остановки", str(e)))

            # Запускаем в фоне
            thread = threading.Thread(target=stop_all_task, daemon=True)
            thread.start()

        except Exception as e:
            logger.error(f"❌ Ошибка массовой остановки через GUI: {e}")
            self._on_mass_operation_error("остановки", str(e))

    def _on_stop_all_completed(self, results):
        """Обработка завершения массовой остановки"""
        from gui.notifications import show_warning, show_info

        self.is_mass_operation_running = False
        self._set_mass_operation_buttons_state(True)

        success_count = sum(1 for success in results.values() if success)
        total_count = len(results)

        if success_count > 0:
            # Перезагружаем интерфейс
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

    def _set_mass_operation_buttons_state(self, enabled: bool):
        """Управляет состоянием кнопок массовых операций"""
        try:
            if hasattr(self, 'start_all_btn'):
                self.start_all_btn.setEnabled(enabled)
                if not enabled:
                    self.start_all_btn.setText("🔄 Запускаем...")
                else:
                    self.start_all_btn.setText("▶️ Запустить все")

            if hasattr(self, 'stop_all_btn'):
                self.stop_all_btn.setEnabled(enabled)
                if not enabled:
                    self.stop_all_btn.setText("🔄 Останавливаем...")
                else:
                    self.stop_all_btn.setText("⏸️ Остановить все")

            if hasattr(self, 'refresh_btn'):
                self.refresh_btn.setEnabled(enabled)

        except Exception as e:
            logger.error(f"❌ Ошибка управления состоянием кнопок: {e}")

    def _on_mass_operation_error(self, operation_type: str, error_message: str):
        """Обработка ошибки массовой операции"""
        from gui.notifications import show_error

        self.is_mass_operation_running = False
        self._set_mass_operation_buttons_state(True)

        show_error(f"Ошибка {operation_type}", f"❌ Ошибка массовой {operation_type}: {error_message}")

    def _on_refresh_profiles_optimized(self):
        """ОПТИМИЗИРОВАННОЕ обновление профилей - НЕ БЛОКИРУЕТ GUI"""
        try:
            from gui.notifications import show_info

            self._set_refresh_button_state(False)
            show_info("Обновление", "Перезагружаем модуль инвайтера в фоне...")

            # АСИНХРОННОЕ обновление
            def refresh_task():
                try:
                    from src.modules.impl.inviter import refresh_inviter_module

                    refresh_inviter_module()

                    # Обновляем GUI в главном потоке
                    QTimer.singleShot(100, self._on_refresh_completed)

                except Exception as e:
                    logger.error(f"❌ Ошибка обновления: {e}")
                    QTimer.singleShot(100, lambda: self._on_refresh_error(str(e)))

            # Запускаем в фоне
            thread = threading.Thread(target=refresh_task, daemon=True)
            thread.start()

        except Exception as e:
            logger.error(f"❌ Ошибка обновления через GUI: {e}")
            self._on_refresh_error(str(e))

    def _on_refresh_completed(self):
        """Обработка завершения обновления"""
        from gui.notifications import show_success

        self._set_refresh_button_state(True)

        # Перезагружаем интерфейс
        self._reload_all_data()

        show_success(
            "Обновление завершено",
            "✅ Модуль инвайтера перезагружен"
        )

        logger.info("🔄 Модуль инвайтера обновлен через GUI")

    def _on_refresh_error(self, error_message):
        """Обработка ошибки обновления"""
        from gui.notifications import show_error

        self._set_refresh_button_state(True)
        show_error("Ошибка обновления", f"Не удалось обновить модуль: {error_message}")

    def _set_refresh_button_state(self, enabled: bool):
        """Управляет состоянием кнопки обновления"""
        try:
            if hasattr(self, 'refresh_btn'):
                self.refresh_btn.setEnabled(enabled)
                if not enabled:
                    self.refresh_btn.setText("🔄 Обновляем...")
                else:
                    self.refresh_btn.setText("🔄 Обновить")
        except Exception as e:
            logger.error(f"❌ Ошибка управления кнопкой обновления: {e}")

    def _create_stats_section(self, layout):
        """Создает секцию статистики с ОПТИМИЗИРОВАННОЙ загрузкой"""
        try:
            # Сначала показываем заглушку
            loading_stats = [
                ("Загрузка...", "...", "#F59E0B", "loading"),
                ("Профилей", "...", "#3B82F6", "profiles"),
                ("Активных", "...", "#10B981", "active"),
                ("Завершено", "...", "#6B7280", "completed")
            ]

            self.stats_widget = InviterStatsWidget(loading_stats)
            layout.addWidget(self.stats_widget)

            # Загружаем реальную статистику АСИНХРОННО
            QTimer.singleShot(500, self._load_stats_async)

            logger.debug("📊 Статистика инвайтера инициализирована с заглушкой")

        except Exception as e:
            logger.error(f"❌ Ошибка создания секции статистики: {e}")

    def _load_stats_async(self):
        """АСИНХРОННАЯ загрузка статистики"""

        def load_task():
            try:
                from src.modules.impl.inviter import get_inviter_stats

                stats_data = get_inviter_stats()

                # Обновляем GUI в главном потоке
                QTimer.singleShot(0, lambda: self._update_stats_widget(stats_data))

            except Exception as e:
                logger.error(f"❌ Ошибка загрузки статистики: {e}")
                # Показываем ошибку в GUI
                QTimer.singleShot(0, self._show_stats_error)

        thread = threading.Thread(target=load_task, daemon=True)
        thread.start()

    def _update_stats_widget(self, stats_data):
        """Обновляет виджет статистики"""
        try:
            for i, (title, value, color, key) in enumerate(stats_data):
                if i < len(self.stats_widget.stat_boxes):
                    self.stats_widget.update_stat(i, value)

            logger.debug("📊 Статистика инвайтера обновлена")

        except Exception as e:
            logger.error(f"❌ Ошибка обновления статистики: {e}")

    def _show_stats_error(self):
        """Показывает ошибку загрузки статистики"""
        error_stats = [
            ("Ошибка", "❌", "#EF4444", "error"),
            ("Загрузки", "0", "#EF4444", "failed")
        ]

        for i, (title, value, color, key) in enumerate(error_stats):
            if i < len(self.stats_widget.stat_boxes):
                self.stats_widget.update_stat(i, value)

    def _create_profiles_section(self, layout):
        """Создает секцию с ОПТИМИЗИРОВАННОЙ таблицей профилей"""
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

        # ОПТИМИЗИРОВАННАЯ таблица профилей
        self.profiles_table = OptimizedInviterTableWidget()
        self.profiles_table.set_parent_manager(self)
        layout.addWidget(self.profiles_table)

    def _on_generate_accounts_report(self):
        """Генерация отчета по аккаунтам с ОПТИМИЗИРОВАННЫМ диалогом"""
        try:
            from gui.dialogs.report_progress_dialog import show_report_progress_dialog
            from PySide6.QtCore import QThread, Signal

            # Показываем диалог прогресса
            progress_dialog = show_report_progress_dialog(self)

            # ОПТИМИЗИРОВАННЫЙ рабочий поток для генерации отчета
            class OptimizedReportWorker(QThread):
                status_update = Signal(str, str)
                progress_update = Signal(int, int)
                finished = Signal(str, dict)
                error = Signal(str)

                def run(self):
                    try:
                        from src.services.account_report_service import AccountReportService

                        self.status_update.emit("Инициализация сервиса отчетов",
                                                "Создаем сервис для сканирования аккаунтов...")

                        # Создаем сервис отчетов
                        report_service = AccountReportService()

                        self.status_update.emit("Сканирование папок аккаунтов",
                                                "Проверяем доступные папки с аккаунтами...")

                        folders_to_scan = [
                            ("Аккаунты", "Основная папка с активными аккаунтами"),
                            ("Списанные", "Аккаунты с ошибками списания"),
                            ("Мертвые", "Заблокированные аккаунты"),
                            ("Замороженные", "Замороженные аккаунты"),
                            ("Спам_блок", "Аккаунты со спам-блоками"),
                            ("Блок_инвайтов", "Аккаунты с блоками инвайтов"),
                            ("Успешно_отработанные", "Успешно завершившие работу"),
                            ("Флуд", "Аккаунты с флуд-лимитами")
                        ]

                        total_folders = len(folders_to_scan)
                        self.progress_update.emit(0, total_folders)

                        # Обрабатываем папки с минимальными задержками
                        for i, (folder_name, folder_desc) in enumerate(folders_to_scan):
                            self.status_update.emit(
                                f"Сканирование папки: {folder_name}",
                                f"📁 {folder_desc}"
                            )

                            # Минимальная задержка для визуализации
                            import time
                            time.sleep(0.1)

                            self.progress_update.emit(i + 1, total_folders)

                        self.status_update.emit("Генерация отчета", "📝 Создаем итоговый файл отчета...")

                        # Генерируем отчет
                        report_path = report_service.generate_report()

                        self.status_update.emit("Сбор статистики", "📊 Подготавливаем краткую сводку...")

                        # Получаем краткую статистику
                        stats = report_service.get_summary_stats()

                        self.status_update.emit("Завершение", "✅ Отчет успешно создан!")

                        self.finished.emit(report_path, stats)

                    except Exception as e:
                        import traceback
                        error_details = f"{str(e)}\n\nДетали:\n{traceback.format_exc()}"
                        self.error.emit(error_details)

            # Создаем и настраиваем рабочий поток
            self.report_worker = OptimizedReportWorker()

            # Обработчики событий
            def on_status_update(status: str, details: str):
                progress_dialog.update_status(status, details)

            def on_progress_update(current: int, total: int):
                progress_dialog.set_progress_range(0, total)
                progress_dialog.set_progress_value(current)

            def on_report_finished(file_path: str, stats: dict):
                progress_dialog.finish_success(file_path, stats)

                logger.info(f"📊 Отчет по аккаунтам создан: {file_path}")

                from gui.notifications import show_success
                from paths import Path
                show_success(
                    "Отчет готов! 📊",
                    f"✅ Отчет по аккаунтам успешно создан!\n\n"
                    f"📊 Статистика:\n"
                    f"👥 Всего аккаунтов: {stats['total_accounts']:,}\n"
                    f"✅ С инвайтами: {stats['accounts_with_invites']:,}\n"
                    f"🎯 Общее количество инвайтов: {stats['total_invites']:,}\n"
                    f"🏆 Лучший аккаунт: {stats['top_account_name']} ({stats['top_account_invites']} инвайтов)\n"
                    f"📁 Папок просканировано: {stats['folders_scanned']}\n\n"
                    f"📄 Файл: {Path(file_path).name}"
                )

                # Пытаемся открыть папку с отчетом
                try:
                    import os
                    import platform
                    from pathlib import Path

                    report_folder = Path(file_path).parent

                    if platform.system() == "Windows":
                        os.startfile(report_folder)
                    elif platform.system() == "Darwin":
                        os.system(f"open '{report_folder}'")
                    else:
                        os.system(f"xdg-open '{report_folder}'")

                except Exception as e:
                    logger.debug(f"Не удалось открыть папку: {e}")

            def on_report_error(error_msg: str):
                progress_dialog.finish_error(error_msg)

                logger.error(f"❌ Ошибка генерации отчета по аккаунтам: {error_msg}")

                from gui.notifications import show_error
                show_error(
                    "Ошибка генерации отчета",
                    f"❌ Не удалось создать отчет:\n\n{error_msg}"
                )

            def on_progress_cancelled():
                if hasattr(self, 'report_worker') and self.report_worker.isRunning():
                    self.report_worker.terminate()
                    self.report_worker.wait()

                from gui.notifications import show_info
                show_info(
                    "Генерация отменена",
                    "Создание отчета было отменено пользователем"
                )

            # Подключаем сигналы
            self.report_worker.status_update.connect(on_status_update)
            self.report_worker.progress_update.connect(on_progress_update)
            self.report_worker.finished.connect(on_report_finished)
            self.report_worker.error.connect(on_report_error)
            progress_dialog.cancelled.connect(on_progress_cancelled)

            # Показываем диалог и запускаем генерацию
            progress_dialog.show()
            self.report_worker.start()

        except Exception as e:
            logger.error(f"❌ Критическая ошибка генерации отчета: {e}")
            from gui.notifications import show_error
            show_error(
                "Критическая ошибка",
                f"Не удалось запустить генерацию отчета:\n{e}"
            )

    def _reload_stats_from_module(self):
        """ОПТИМИЗИРОВАННАЯ перезагрузка статистики"""
        # Запускаем асинхронно
        QTimer.singleShot(0, self._load_stats_async)

    def _reload_all_data(self):
        """ОПТИМИЗИРОВАННАЯ перезагрузка всех данных"""
        try:
            logger.debug("🔄 ОПТИМИЗИРОВАННАЯ перезагрузка всех данных...")

            # Обновляем статистику асинхронно
            self._reload_stats_from_module()

            # Обновляем таблицу профилей
            if hasattr(self, 'profiles_table'):
                self.profiles_table.refresh_data()

            logger.debug("✅ Все данные обновлены из модуля")

        except Exception as e:
            logger.error(f"❌ Ошибка перезагрузки данных из модуля: {e}")

    def refresh_data(self):
        """ОСНОВНОЙ метод обновления данных - ОПТИМИЗИРОВАННЫЙ"""
        try:
            logger.info("🔄 ОПТИМИЗИРОВАННОЕ обновление данных GUI инвайтера...")

            # Перезагружаем все данные оптимизированно
            self._reload_all_data()

            logger.info("✅ Данные GUI инвайтера обновлены оптимизированно")

        except Exception as e:
            logger.error(f"❌ Ошибка оптимизированного обновления данных: {e}")

    def start_animation(self):
        """Запускает анимацию появления"""
        try:
            # Анимация статистики
            if hasattr(self, 'stats_widget'):
                QTimer.singleShot(100, self.stats_widget.animate_appearance)

            # Анимация таблицы
            if hasattr(self, 'profiles_table'):
                QTimer.singleShot(300, self.profiles_table.animate_appearance)

            logger.debug("🎬 ОПТИМИЗИРОВАННЫЕ анимации GUI инвайтера запущены")

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
                    'stats_cache': _inviter_module_manager._stats_cache,
                    'background_workers': hasattr(self, 'worker_manager') and self.worker_manager.is_initialized
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
                    f"🚀 Активных процессов: {status.get('active_processes', 0)}\n"
                    f"🔧 Фоновые рабочие: {'✅' if status.get('background_workers') else '❌'}"
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
        """Деструктор - корректно останавливаем фоновых рабочих"""
        try:
            # Останавливаем массовые операции
            self.is_mass_operation_running = False

            # Останавливаем фоновых рабочих
            if hasattr(self, 'worker_manager') and self.worker_manager:
                from gui.workers.background_workers import shutdown_worker_manager
                shutdown_worker_manager()

            # При закрытии GUI останавливаем все процессы
            from src.modules.impl.inviter import stop_all_profiles
            stop_all_profiles()

            logger.debug("🔄 ОПТИМИЗИРОВАННЫЙ GUI инвайтера закрыт, все ресурсы освобождены")
        except:
            pass  # Игнорируем ошибки при закрытии