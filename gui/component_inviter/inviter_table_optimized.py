# gui/component_inviter/inviter_table_optimized.py - ОПТИМИЗИРОВАННАЯ ВЕРСИЯ
"""
ОПТИМИЗИРОВАННАЯ таблица профилей инвайтера - НЕ БЛОКИРУЕТ GUI
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QFrame,
    QLabel, QPushButton, QComboBox, QSpinBox, QCheckBox,
    QProgressBar, QSizePolicy, QGraphicsOpacityEffect, QLineEdit,
    QGridLayout
)
from PySide6.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve, Signal,
    QParallelAnimationGroup, QMutex, QMutexLocker
)
from PySide6.QtGui import QFont, QColor, QPainter, QPen, QBrush
from loguru import logger
from typing import Optional, Dict, List
import time


class OptimizedInviterProfileRow(QWidget):
    """ОПТИМИЗИРОВАННАЯ строка профиля - минимум обновлений"""

    # Сигналы
    profile_started = Signal(str)
    profile_stopped = Signal(str)
    profile_deleted = Signal(str)
    settings_changed = Signal(str, dict)

    def __init__(self, profile_data):
        super().__init__()
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.profile_data = profile_data
        self.profile_name = profile_data.get('name', 'Профиль')
        self.is_running = profile_data.get('is_running', False)

        # КЭШИРОВАНИЕ для предотвращения частых обновлений
        self._cached_stats = {}
        self._last_update_time = 0
        self._update_interval = 2.0  # Минимум 2 секунды между обновлениями

        # Мьютекс для безопасности потоков
        self.mutex = QMutex()

        # Флаги состояния
        self.manually_stopped = False
        self.is_expanded = False
        self.is_updating = False

        # Загружаем данные из профиля
        self.users_list = profile_data.get('users_list', [])
        self.chats_list = profile_data.get('chats_list', [])
        self.extended_settings = profile_data.get('extended_settings', {})
        self.process_stats = profile_data.get('process_stats', {})

        self.bot_account = profile_data.get('bot_account', None)
        if not self.bot_account and profile_data.get('config', {}).get('bot_account'):
            self.bot_account = profile_data['config']['bot_account']

        # ОПТИМИЗИРОВАННЫЕ таймеры - РЕЖЕ ОБНОВЛЕНИЯ
        self.progress_timer = QTimer()
        self.progress_timer.timeout.connect(self._optimized_update_progress)
        self.progress_timer.setSingleShot(False)

        self.completion_timer = QTimer()
        self.completion_timer.timeout.connect(self._optimized_check_completion)
        self.completion_timer.setSingleShot(False)

        # УБИРАЕМ chat_stats_timer - это будет делать фоновый рабочий

        self.setObjectName("InviterProfileRow")
        self.setMinimumHeight(85)

        # Инициализация UI элементов
        self.users_btn = None
        self.chats_btn = None
        self.settings_btn = None
        self.delete_btn = None
        self.start_stop_btn = None
        self.name_edit = None
        self.invite_type_combo = None
        self.manage_admins_btn = None
        self.bot_token_btn = None

        # Создаем UI
        self._create_optimized_ui()
        self._apply_styles()
        self._connect_signals()

        # РЕГИСТРИРУЕМ в фоновом мониторинге
        self._register_for_background_monitoring()

        # Если процесс запущен - запускаем РЕДКИЕ обновления
        if self.is_running:
            self.progress_timer.start(3000)  # Каждые 3 секунды вместо 1
            self.completion_timer.start(5000)  # Каждые 5 секунд вместо 0.5

        # Синхронизация с модулем через 1 секунду
        QTimer.singleShot(1000, self.sync_with_module_state)

    def _register_for_background_monitoring(self):
        """Регистрирует профиль для фонового мониторинга"""
        try:
            from gui.workers.background_workers import get_worker_manager

            worker_manager = get_worker_manager()
            if worker_manager and worker_manager.is_initialized:
                worker_manager.add_profile_monitoring(self.profile_name)

                # Подключаемся к сигналам фонового рабочего
                if worker_manager.profile_stats_worker:
                    worker_manager.profile_stats_worker.stats_updated.connect(
                        self._on_background_stats_updated
                    )

                logger.debug(f"📊 Профиль {self.profile_name} зарегистрирован для фонового мониторинга")

        except Exception as e:
            logger.error(f"❌ Ошибка регистрации фонового мониторинга: {e}")

    def _on_background_stats_updated(self, profile_name: str, stats_data: dict):
        """Обрабатывает обновления от фонового рабочего"""
        if profile_name != self.profile_name:
            return

        try:
            with QMutexLocker(self.mutex):
                # Проверяем изменились ли данные
                if stats_data != self._cached_stats:
                    self._cached_stats = stats_data

                    # Обновляем UI элементы БЕЗ обращения к модулю
                    self._update_ui_from_cached_stats(stats_data)

        except Exception as e:
            logger.error(f"❌ Ошибка обработки фоновых статистик: {e}")

    def _update_ui_from_cached_stats(self, stats_data: dict):
        """Обновляет UI на основе кэшированных данных"""
        try:
            # Обновляем прогресс
            if hasattr(self, 'progress_bar') and self.progress_bar:
                total_goal = stats_data.get('total_goal', 0)
                success = stats_data.get('success', 0)

                if total_goal > 0:
                    self.progress_bar.setRange(0, total_goal)
                    self.progress_bar.setValue(success)
                    self.progress_bar.setFormat(f"{success}/{total_goal}")

            # Обновляем счетчики
            if hasattr(self, 'success_label') and self.success_label:
                self.success_label.setText(f"✅{stats_data.get('success', 0)}")

            if hasattr(self, 'errors_label') and self.errors_label:
                self.errors_label.setText(f"❌{stats_data.get('errors', 0)}")

            if hasattr(self, 'speed_label') and self.speed_label:
                self.speed_label.setText(f"⚡{stats_data.get('speed', 0)}")

            # Обновляем статус
            if hasattr(self, 'status_label') and self.status_label:
                status = stats_data.get('status', 'Неизвестно')
                self.status_label.setText(status)

            # Обновляем состояние запуска
            is_running = stats_data.get('is_running', False)
            if self.is_running != is_running:
                self.update_running_state(is_running)

        except Exception as e:
            logger.error(f"❌ Ошибка обновления UI из кэша: {e}")

    def _create_optimized_ui(self):
        """Создает оптимизированный UI"""
        # Основной layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 6, 10, 6)
        main_layout.setSpacing(0)

        # Создаем шапку как отдельный виджет с фиксированной высотой
        self.header_widget = QWidget()
        self.header_widget.setFixedHeight(85)
        self._create_compact_header_content(self.header_widget)

        main_layout.addWidget(self.header_widget)

        # Раскрывающаяся секция (создается при необходимости)
        self.expandable_widget = None

    def _create_compact_header_content(self, header_widget):
        """Создает содержимое шапки внутри отдельного виджета"""
        layout = QHBoxLayout(header_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Кнопка раскрытия
        self.expand_button = self._create_expand_button()
        layout.addWidget(self.expand_button)

        # Все остальные элементы шапки
        status_widget = self._create_compact_status()
        layout.addWidget(status_widget)

        start_widget = self._create_compact_start_button()
        layout.addWidget(start_widget)

        name_widget = self._create_compact_name()
        layout.addWidget(name_widget)

        type_widget = self._create_compact_invite_type()
        layout.addWidget(type_widget)

        users_widget = self._create_compact_users_base()
        layout.addWidget(users_widget)

        chats_widget = self._create_compact_chats_base()
        layout.addWidget(chats_widget)

        progress_widget = self._create_inline_progress()
        layout.addWidget(progress_widget)

        self.control_buttons_widget = self._create_compact_control_buttons()
        layout.addWidget(self.control_buttons_widget)

    def _create_expand_button(self):
        """Создает кнопку раскрытия"""
        button = QPushButton("▼")
        button.setFixedSize(24, 24)
        button.setObjectName("ExpandButton")
        button.clicked.connect(self._toggle_expansion_optimized)
        button.setStyleSheet("""
            QPushButton#ExpandButton {
                background: rgba(59, 130, 246, 0.2);
                border: 1px solid rgba(59, 130, 246, 0.4);
                border-radius: 4px;
                color: #FFFFFF;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton#ExpandButton:hover {
                background: rgba(59, 130, 246, 0.3);
            }
        """)
        return button

    def _toggle_expansion_optimized(self):
        """ОПТИМИЗИРОВАННОЕ переключение раскрытия"""
        self.is_expanded = not self.is_expanded

        if self.is_expanded:
            self.expand_button.setText("▲")
            # Создаем секцию только при раскрытии
            if not self.expandable_widget:
                self._create_expandable_section_lazy()
        else:
            self.expand_button.setText("▼")
            # Скрываем секцию
            if self.expandable_widget:
                self.expandable_widget.hide()

    def _create_expandable_section_lazy(self):
        """ЛЕНИВОЕ создание раскрывающейся секции"""
        if self.expandable_widget:
            return

        self.expandable_widget = QWidget()
        self.expandable_widget.setFixedHeight(200)  # Фиксированная высота

        layout = QVBoxLayout(self.expandable_widget)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(6)

        # Заглушка для статистики чатов
        placeholder = QLabel("📊 Детальная статистика чатов загружается...")
        placeholder.setAlignment(Qt.AlignCenter)
        placeholder.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 0.6);
                font-size: 14px;
                padding: 20px;
                background: rgba(59, 130, 246, 0.1);
                border-radius: 8px;
                border: 1px solid rgba(59, 130, 246, 0.2);
            }
        """)

        layout.addWidget(placeholder)

        # Добавляем в главный layout
        main_layout = self.layout()
        main_layout.addWidget(self.expandable_widget)

        # Показываем
        self.expandable_widget.show()

    def _create_compact_status(self):
        """Компактный индикатор статуса"""
        widget = QWidget()
        widget.setFixedWidth(40)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignCenter)

        self.status_indicator = QLabel("●")
        self.status_indicator.setAlignment(Qt.AlignCenter)
        self.status_indicator.setStyleSheet(f"""
            QLabel {{
                font-size: 14px;
                color: {'#10B981' if self.is_running else '#6B7280'};
                font-weight: bold;
            }}
        """)

        layout.addWidget(self.status_indicator)
        return widget

    def _create_compact_start_button(self):
        """Компактная кнопка запуска"""
        widget = QWidget()
        widget.setFixedWidth(80)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignCenter)

        self.start_stop_btn = QPushButton()
        self._update_start_button()
        self.start_stop_btn.setFixedSize(70, 28)

        layout.addWidget(self.start_stop_btn)
        return widget

    def _create_compact_name(self):
        """Компактное поле названия"""
        widget = QWidget()
        widget.setFixedWidth(150)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        name_label = QLabel("Профиль:")
        name_label.setStyleSheet("font-size: 10px; color: rgba(255,255,255,0.6);")

        self.name_edit = QLineEdit(self.profile_name)
        self.name_edit.setFixedWidth(140)
        self.name_edit.setFixedHeight(24)
        self.name_edit.setStyleSheet("""
            QLineEdit {
                background: #111827;
                border: 1px solid #374151;
                border-radius: 3px;
                color: #FFFFFF;
                font-size: 12px;
                padding: 2px 4px;
            }
            QLineEdit:focus {
                border-color: #2563EB;
            }
        """)

        layout.addWidget(name_label)
        layout.addWidget(self.name_edit)
        return widget

    def _create_compact_invite_type(self):
        """Компактный селектор типа инвайта"""
        widget = QWidget()
        widget.setFixedWidth(120)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        type_label = QLabel("Тип:")
        type_label.setStyleSheet("font-size: 10px; color: rgba(255,255,255,0.6);")

        self.invite_type_combo = QComboBox()
        self.invite_type_combo.addItems(["Классический", "Через админку"])
        self.invite_type_combo.setFixedWidth(110)
        self.invite_type_combo.setFixedHeight(24)
        self.invite_type_combo.setStyleSheet("""
            QComboBox {
                background: #111827;
                border: 1px solid #374151;
                border-radius: 3px;
                color: #FFFFFF;
                font-size: 11px;
                padding: 2px 4px;
            }
            QComboBox:focus {
                border-color: #2563EB;
            }
            QComboBox QAbstractItemView {
                background: #1F2937;
                border: 1px solid #374151;
                selection-background-color: #2563EB;
                color: #FFFFFF;
                font-size: 11px;
            }
        """)

        current_type = self.profile_data.get('config', {}).get('invite_type', 'classic')
        if current_type == 'admin':
            self.invite_type_combo.setCurrentText("Через админку")
        else:
            self.invite_type_combo.setCurrentText("Классический")

        layout.addWidget(type_label)
        layout.addWidget(self.invite_type_combo)
        return widget

    def _create_compact_users_base(self):
        """Компактная база пользователей"""
        widget = QWidget()
        widget.setFixedWidth(80)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        label = QLabel("Юзеры:")
        label.setStyleSheet("font-size: 10px; color: rgba(255,255,255,0.6);")

        users_count = len(self.users_list)
        if users_count >= 1000000:
            button_text = f"{users_count // 1000000}.{(users_count % 1000000) // 100000}M"
        elif users_count >= 1000:
            button_text = f"{users_count // 1000}K"
        else:
            button_text = f"{users_count}"

        self.users_btn = QPushButton(f"👥{button_text}")
        self.users_btn.setFixedHeight(24)
        self.users_btn.setFixedWidth(70)
        self.users_btn.setToolTip(f"Всего пользователей: {users_count:,}")
        self.users_btn.setStyleSheet("""
            QPushButton {
                background: rgba(59, 130, 246, 0.2);
                border: 1px solid rgba(59, 130, 246, 0.5);
                border-radius: 3px;
                color: #FFFFFF;
                font-size: 11px;
                font-weight: 600;
                padding: 0 4px;
            }
            QPushButton:hover {
                background: rgba(59, 130, 246, 0.3);
            }
        """)

        layout.addWidget(label)
        layout.addWidget(self.users_btn)
        return widget

    def _create_compact_chats_base(self):
        """Компактная база чатов"""
        widget = QWidget()
        widget.setFixedWidth(80)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        label = QLabel("Чаты:")
        label.setStyleSheet("font-size: 10px; color: rgba(255,255,255,0.6);")

        chats_count = len(self.chats_list)
        if chats_count >= 1000:
            button_text = f"{chats_count // 1000}K"
        else:
            button_text = f"{chats_count}"

        self.chats_btn = QPushButton(f"💬{button_text}")
        self.chats_btn.setFixedHeight(24)
        self.chats_btn.setFixedWidth(70)
        self.chats_btn.setToolTip(f"Всего чатов: {chats_count:,}")
        self.chats_btn.setStyleSheet("""
            QPushButton {
                background: rgba(16, 185, 129, 0.2);
                border: 1px solid rgba(16, 185, 129, 0.5);
                border-radius: 3px;
                color: #FFFFFF;
                font-size: 11px;
                font-weight: 600;
                padding: 0 4px;
            }
            QPushButton:hover {
                background: rgba(16, 185, 129, 0.3);
            }
        """)

        layout.addWidget(label)
        layout.addWidget(self.chats_btn)
        return widget

    def _create_inline_progress(self):
        """Прогресс и статистика в одну строку"""
        widget = QWidget()
        widget.setFixedWidth(200)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        # Метка
        progress_label = QLabel("Прогресс:")
        progress_label.setStyleSheet("font-size: 10px; color: rgba(255,255,255,0.6);")

        # Строка с прогрессом и статистикой
        progress_layout = QHBoxLayout()
        progress_layout.setSpacing(4)

        # Мини прогресс-бар
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(16)
        self.progress_bar.setFixedWidth(100)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%v/%m")
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 6px;
                background: rgba(255, 255, 255, 0.1);
                text-align: center;
                color: #FFFFFF;
                font-size: 8px;
                font-weight: 600;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3B82F6, stop:1 #8B5CF6);
                border-radius: 5px;
            }
        """)

        # Компактная статистика
        self.success_label = QLabel("✅0")
        self.success_label.setStyleSheet("font-size: 10px; color: #10B981; font-weight: 600;")

        self.errors_label = QLabel("❌0")
        self.errors_label.setStyleSheet("font-size: 10px; color: #EF4444; font-weight: 600;")

        self.speed_label = QLabel("⚡0")
        self.speed_label.setStyleSheet("font-size: 10px; color: #F59E0B; font-weight: 600;")

        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.success_label)
        progress_layout.addWidget(self.errors_label)
        progress_layout.addWidget(self.speed_label)

        # Статус
        self.status_label = QLabel("Ожидание...")
        self.status_label.setStyleSheet("font-size: 9px; color: rgba(255,255,255,0.5);")

        layout.addWidget(progress_label)
        layout.addLayout(progress_layout)
        layout.addWidget(self.status_label)

        return widget

    def _create_compact_control_buttons(self):
        """Компактные кнопки управления"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)

        current_type = self.profile_data.get('config', {}).get('invite_type', 'classic')
        is_admin_mode = current_type == 'admin' or (
                self.invite_type_combo and self.invite_type_combo.currentText() == "Через админку"
        )

        if is_admin_mode:
            # Кнопки для режима админки (компактные)
            self.manage_admins_btn = QPushButton("👑")
            self.manage_admins_btn.setFixedSize(28, 28)
            self.manage_admins_btn.setToolTip("Управление главными администраторами")

            self.bot_token_btn = QPushButton("🤖")
            self.bot_token_btn.setFixedSize(28, 28)
            self.bot_token_btn.setToolTip("Настройка токена бота")

            layout.addWidget(self.manage_admins_btn)
            layout.addWidget(self.bot_token_btn)
            widget.setFixedWidth(120)
        else:
            self.manage_admins_btn = None
            self.bot_token_btn = None
            widget.setFixedWidth(80)

        # Основные кнопки (компактные)
        self.settings_btn = QPushButton("⚙️")
        self.settings_btn.setFixedSize(28, 28)
        self.settings_btn.setToolTip("Расширенные настройки")

        self.delete_btn = QPushButton("🗑️")
        self.delete_btn.setFixedSize(28, 28)
        self.delete_btn.setToolTip("Удалить профиль")

        # Общие стили для всех кнопок
        button_style = """
            QPushButton {
                background: rgba(156, 163, 175, 0.2);
                border: 1px solid rgba(156, 163, 175, 0.5);
                border-radius: 4px;
                color: #FFFFFF;
                font-size: 11px;
            }
            QPushButton:hover {
                background: rgba(156, 163, 175, 0.3);
            }
        """

        if hasattr(self, 'manage_admins_btn') and self.manage_admins_btn:
            self.manage_admins_btn.setStyleSheet(button_style.replace("156, 163, 175", "139, 92, 246"))
        if hasattr(self, 'bot_token_btn') and self.bot_token_btn:
            self.bot_token_btn.setStyleSheet(button_style.replace("156, 163, 175", "245, 158, 11"))

        self.settings_btn.setStyleSheet(button_style)
        self.delete_btn.setStyleSheet(button_style.replace("156, 163, 175", "239, 68, 68"))

        layout.addWidget(self.settings_btn)
        layout.addWidget(self.delete_btn)

        return widget

    def _apply_styles(self):
        """Применяет стили к строке профиля"""
        self.setStyleSheet("""
            QWidget#InviterProfileRow {
                background: #1F2937;
                border: 1px solid #4B5563;
                border-radius: 8px;
                padding: 8px;
                margin: 6px 0;
            }
            QWidget#InviterProfileRow:hover {
                background: #374151;
                border: 1px solid #2563EB;
            }
        """)

    def _connect_signals(self):
        """Подключает все сигналы к кнопкам"""
        try:
            if self.users_btn:
                self.users_btn.clicked.connect(self._on_users_settings)

            if self.chats_btn:
                self.chats_btn.clicked.connect(self._on_chats_settings)

            if self.start_stop_btn:
                self.start_stop_btn.clicked.connect(self._toggle_profile)

            if self.name_edit:
                self.name_edit.textChanged.connect(self._on_name_changed)

            if self.invite_type_combo:
                self.invite_type_combo.currentTextChanged.connect(self._on_invite_type_changed_simple)

            self._reconnect_control_signals()

        except Exception as e:
            logger.error(f"❌ Ошибка подключения сигналов для {self.profile_name}: {e}")

    def _optimized_update_progress(self):
        """ОПТИМИЗИРОВАННОЕ обновление прогресса - БЕЗ обращения к модулю"""
        # Теперь обновления приходят через фоновый рабочий поток
        # Этот метод может быть пустым или делать минимальные проверки
        pass

    def _optimized_check_completion(self):
        """ОПТИМИЗИРОВАННАЯ проверка завершения"""
        # Минимальная проверка только через фоновый рабочий
        pass

    def sync_with_module_state(self):
        """ОПТИМИЗИРОВАННАЯ синхронизация состояния с модулем"""
        try:
            from src.modules.impl.inviter.inviter_manager import _inviter_module_manager

            if not _inviter_module_manager:
                return

            # Только быстрая проверка состояния
            is_actually_running = self.profile_name in _inviter_module_manager.active_processes

            if self.is_running != is_actually_running:
                self.update_running_state(is_actually_running)

        except Exception as e:
            logger.error(f"❌ Ошибка синхронизации состояния: {e}")

    def update_running_state(self, is_running: bool):
        """Обновление состояния профиля"""
        old_state = self.is_running
        self.is_running = is_running

        # Обновляем индикатор статуса
        if hasattr(self, 'status_indicator'):
            if is_running:
                self.status_indicator.setStyleSheet("""
                    QLabel {
                        font-size: 14px;
                        color: #10B981;
                        font-weight: bold;
                    }
                """)
            else:
                self.status_indicator.setStyleSheet("""
                    QLabel {
                        font-size: 14px;
                        color: #6B7280;
                        font-weight: bold;
                    }
                """)

        # Обновляем кнопку запуска/остановки
        self._update_start_button()

        # Управляем таймерами - РЕДКИЕ обновления
        if self.is_running:
            if hasattr(self, 'progress_timer'):
                self.progress_timer.start(3000)  # Каждые 3 секунды
            if hasattr(self, 'completion_timer'):
                self.completion_timer.start(5000)  # Каждые 5 секунд
            if hasattr(self, 'status_label'):
                self.status_label.setText("🚀 Запущен...")
        else:
            if hasattr(self, 'progress_timer'):
                self.progress_timer.stop()
            if hasattr(self, 'completion_timer'):
                self.completion_timer.stop()

            if hasattr(self, 'status_label'):
                if self.manually_stopped:
                    self.status_label.setText("⏹️ Остановлен пользователем")
                else:
                    self.status_label.setText("✅ Работа завершена")

    def _update_start_button(self):
        """Обновляет текст и цвет кнопки в зависимости от состояния"""
        if not hasattr(self, 'start_stop_btn') or not self.start_stop_btn:
            return

        if self.is_running:
            self.start_stop_btn.setText("Стоп")
            self.start_stop_btn.setStyleSheet("""
                QPushButton {
                    background: #EF4444;
                    color: white;
                    border-radius: 6px;
                    font-weight: 600;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background: #DC2626;
                }
                QPushButton:pressed {
                    background: #B91C1C;
                }
            """)
        else:
            self.start_stop_btn.setText("Запуск")
            self.start_stop_btn.setStyleSheet("""
                QPushButton {
                    background: #10B981;
                    color: white;
                    border-radius: 6px;
                    font-weight: 600;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background: #059669;
                }
                QPushButton:pressed {
                    background: #047857;
                }
            """)

    def _toggle_profile(self):
        """Переключение состояния профиля"""
        if self.is_running:
            logger.info(f"🛑 Пользователь вручную останавливает профиль: {self.profile_name}")
            self.manually_stopped = True
            self.profile_stopped.emit(self.profile_name)
        else:
            logger.info(f"🚀 Пользователь запускает профиль: {self.profile_name}")
            self.manually_stopped = False
            self.profile_started.emit(self.profile_name)

    # Остальные методы остаются без изменений...
    def _on_name_changed(self):
        """Обработчик изменения имени профиля"""
        if not self.name_edit:
            return

        new_name = self.name_edit.text().strip() or self.profile_name
        if new_name != self.profile_name:
            self.profile_name = new_name
            self.settings_changed.emit(self.profile_name, {'name': new_name})

    def _on_invite_type_changed_simple(self, new_type: str):
        """Простая смена типа с обновлением кнопок"""
        try:
            logger.debug(f"🔄 Изменен тип инвайта на: {new_type}")

            if new_type == "Через админку":
                self._save_invite_type_settings('admin')
            else:
                self._save_invite_type_settings('classic')

            self._update_control_buttons_visibility()

        except Exception as e:
            logger.error(f"❌ Ошибка изменения типа инвайта: {e}")

    def _update_control_buttons_visibility(self):
        """Обновляет видимость кнопок управления"""
        try:
            if hasattr(self, 'control_buttons_widget'):
                header_widget = self.findChild(QWidget)
                if header_widget:
                    layout = header_widget.layout()
                    if layout:
                        old_widget = self.control_buttons_widget
                        layout.removeWidget(old_widget)
                        old_widget.deleteLater()

                        self.control_buttons_widget = self._create_compact_control_buttons()
                        layout.addWidget(self.control_buttons_widget)

                        self._reconnect_control_signals()

        except Exception as e:
            logger.error(f"❌ Ошибка обновления кнопок управления: {e}")

    def _reconnect_control_signals(self):
        """Переподключает сигналы кнопок управления"""
        try:
            if hasattr(self, 'manage_admins_btn') and self.manage_admins_btn:
                self.manage_admins_btn.clicked.connect(self._on_manage_admins)

            if hasattr(self, 'bot_token_btn') and self.bot_token_btn:
                self.bot_token_btn.clicked.connect(self._on_bot_token_settings)

            if self.settings_btn:
                self.settings_btn.clicked.connect(self._on_extended_settings)

            if self.delete_btn:
                self.delete_btn.clicked.connect(self._delete_profile)

        except Exception as e:
            logger.error(f"❌ Ошибка переподключения сигналов кнопок: {e}")

    def _save_invite_type_settings(self, invite_type: str):
        """Сохраняет настройки типа инвайта"""
        try:
            config_update = {'invite_type': invite_type}

            from src.modules.impl.inviter import update_profile_config
            success = update_profile_config(self.profile_name, config_update)

            if success:
                if 'config' not in self.profile_data:
                    self.profile_data['config'] = {}
                self.profile_data['config'].update(config_update)

                logger.debug(f"✅ Настройки типа инвайта сохранены: {invite_type}")
            else:
                logger.error("❌ Не удалось сохранить настройки типа инвайта")

        except Exception as e:
            logger.error(f"❌ Ошибка сохранения настроек типа инвайта: {e}")

    def _on_users_settings(self):
        """Настройка базы пользователей"""
        try:
            from gui.dialogs.inviter_dialogs import show_users_base_dialog

            actual_users = self._load_actual_users_from_file()
            users = show_users_base_dialog(self, actual_users, self.profile_name)

            if users is not None:
                from src.modules.impl.inviter import update_profile_users

                success = update_profile_users(self.profile_name, users)

                if success:
                    self.users_list = users
                    users_count = len(users)

                    if users_count >= 1000000:
                        button_text = f"👥{users_count // 1000000}.{(users_count % 1000000) // 100000}M"
                    elif users_count >= 1000:
                        button_text = f"👥{users_count // 1000}K"
                    else:
                        button_text = f"👥{users_count}"

                    if self.users_btn:
                        self.users_btn.setText(button_text)
                        self.users_btn.setToolTip(f"Всего пользователей: {users_count:,}")

                    logger.info(f"✅ База пользователей обновлена для {self.profile_name}: {users_count} пользователей")

                    try:
                        from gui.notifications import show_success
                        show_success(
                            "База пользователей",
                            f"✅ Сохранено {users_count:,} пользователей\nВ файл: База юзеров.txt"
                        )
                    except:
                        pass

        except Exception as e:
            logger.error(f"❌ Ошибка настройки пользователей: {e}")

    def _on_chats_settings(self):
        """Настройка базы чатов"""
        try:
            from gui.dialogs.inviter_dialogs import show_chats_base_dialog

            current_chats = getattr(self, 'chats_list', [])
            chats = show_chats_base_dialog(self, current_chats)

            if chats is not None:
                from src.modules.impl.inviter import update_profile_chats

                success = update_profile_chats(self.profile_name, chats)

                if success:
                    self.chats_list = chats
                    chats_count = len(chats)

                    if chats_count >= 1000:
                        button_text = f"💬{chats_count // 1000}K"
                    else:
                        button_text = f"💬{chats_count}"

                    if self.chats_btn:
                        self.chats_btn.setText(button_text)
                        self.chats_btn.setToolTip(f"Всего чатов: {chats_count:,}")

                    logger.info(f"✅ База чатов обновлена для {self.profile_name}: {chats_count} чатов")

                    try:
                        from gui.notifications import show_success
                        show_success(
                            "База чатов",
                            f"✅ Сохранено {chats_count:,} чатов\nВ файл: База чатов.txt"
                        )
                    except:
                        pass

        except Exception as e:
            logger.error(f"❌ Ошибка настройки чатов: {e}")

    def _on_extended_settings(self):
        """Расширенные настройки профиля"""
        try:
            from gui.dialogs.inviter_dialogs import show_extended_settings_dialog
            from src.modules.impl.inviter.inviter_manager import _inviter_module_manager

            if _inviter_module_manager:
                fresh_profile = _inviter_module_manager.profile_manager.get_profile(self.profile_name)
                if fresh_profile:
                    current_config = fresh_profile.get('config', {})
                else:
                    current_config = self.profile_data.get('config', {})
            else:
                current_config = self.profile_data.get('config', {})

            new_settings = show_extended_settings_dialog(self, current_config)

            if new_settings is not None:
                self._save_extended_settings_to_module(new_settings)
                logger.info(f"⚙️ Обновлены расширенные настройки для {self.profile_name}")

        except Exception as e:
            logger.error(f"❌ Ошибка настройки профиля: {e}")

    def _save_extended_settings_to_module(self, settings: dict):
        """Сохраняет расширенные настройки через модуль"""
        try:
            from src.modules.impl.inviter import update_profile_config

            success = update_profile_config(self.profile_name, settings)

            if success:
                if 'config' not in self.profile_data:
                    self.profile_data['config'] = {}

                self.profile_data['config'].update(settings)
                self.extended_settings = settings

                logger.info(f"✅ Настройки сохранены в JSON для {self.profile_name}")

                try:
                    from gui.notifications import show_success
                    show_success(
                        "Настройки сохранены",
                        f"Расширенные настройки профиля '{self.profile_name}' успешно сохранены"
                    )
                except:
                    pass

        except Exception as e:
            logger.error(f"❌ Ошибка сохранения настроек в модуль: {e}")

    def _on_manage_admins(self):
        """Обработчик кнопки управления главными админами"""
        try:
            from gui.dialogs.main_admins_dialog import show_main_admins_dialog

            logger.info(f"👑 Открываем диалог управления админами для профиля: {self.profile_name}")

            selected_admins = show_main_admins_dialog(self, self.profile_name)

            if selected_admins:
                logger.info(f"✅ Выбрано главных админов: {len(selected_admins)}")

                try:
                    from gui.notifications import show_success
                    show_success(
                        "Главные админы",
                        f"✅ Назначено {len(selected_admins)} главных администраторов\n"
                        f"Аккаунты перемещены в папку '{self.profile_name}/Админы/'"
                    )
                except:
                    pass

        except Exception as e:
            logger.error(f"❌ Ошибка управления админами: {e}")

    def _on_bot_token_settings(self):
        """Обработчик кнопки настройки токенов ботов"""
        try:
            from gui.dialogs.bot_token_dialog import show_bot_tokens_dialog

            logger.info(f"🤖 Открываем диалог настройки токенов ботов для профиля: {self.profile_name}")

            saved_tokens = show_bot_tokens_dialog(self, self.profile_name)

            if saved_tokens:
                logger.info(f"✅ Токены ботов настроены для профиля: {self.profile_name}")

                try:
                    from gui.notifications import show_success
                    show_success(
                        "Токены ботов",
                        f"🤖 Сохранено {len(saved_tokens)} токенов ботов\n"
                        f"Файл: {self.profile_name}/bot_tokens.txt"
                    )
                except:
                    pass

        except Exception as e:
            logger.error(f"❌ Ошибка настройки токенов ботов: {e}")

    def _delete_profile(self):
        """Удаляет профиль"""
        self.profile_deleted.emit(self.profile_name)

    def _load_actual_users_from_file(self) -> List[str]:
        """Загружает актуальные данные пользователей из файла"""
        try:
            from src.modules.impl.inviter import get_profile_users_from_file

            actual_users = get_profile_users_from_file(self.profile_name)

            if actual_users is not None:
                return actual_users
            else:
                return getattr(self, 'users_list', [])

        except Exception as e:
            logger.error(f"❌ Ошибка загрузки пользователей из файла для {self.profile_name}: {e}")
            return getattr(self, 'users_list', [])

    def update_progress(self, done: int, total: int):
        """Обновляем прогресс-бар напрямую"""
        if self.progress_bar:
            self.progress_bar.setRange(0, total)
            self.progress_bar.setValue(done)

    def update_counters(self, success, errors, total):
        """Обновляет счетчики"""
        if hasattr(self, 'success_label'):
            self.success_label.setText(f"✅{success}")
        if hasattr(self, 'errors_label'):
            self.errors_label.setText(f"❌{errors}")

    def update_last_action(self, action_text):
        """Обновляет текст последнего действия"""
        if hasattr(self, 'status_label'):
            self.status_label.setText(action_text)

    def __del__(self):
        """Деструктор - отписываемся от фонового мониторинга"""
        try:
            from gui.workers.background_workers import get_worker_manager

            worker_manager = get_worker_manager()
            if worker_manager:
                worker_manager.remove_profile_monitoring(self.profile_name)
        except:
            pass


class OptimizedInviterTableWidget(QWidget):
    """ОПТИМИЗИРОВАННАЯ основная таблица с профилями инвайтера"""

    def __init__(self):
        super().__init__()
        self.setObjectName("InviterTableWidget")
        self.profile_rows = {}

        # Основной layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Создаем скролл область
        self._create_scroll_area(layout)

        # ИНИЦИАЛИЗИРУЕМ ФОНОВЫЕ РАБОЧИЕ
        self._init_background_workers()

        # Загружаем данные из модуля
        self._load_profiles_from_module()

        # Эффект прозрачности для анимации
        effect = QGraphicsOpacityEffect()
        effect.setOpacity(0.0)
        self.setGraphicsEffect(effect)

        # УБИРАЕМ частый sync_timer - теперь всё через фоновые рабочие
        # self.sync_timer = QTimer()
        # self.sync_timer.timeout.connect(self.force_sync_all_profiles)
        # self.sync_timer.start(5000)

    def _init_background_workers(self):
        """Инициализирует фоновых рабочих"""
        try:
            from gui.workers.background_workers import init_worker_manager

            self.worker_manager = init_worker_manager()
            logger.info("✅ Фоновые рабочие инициализированы для таблицы")

        except Exception as e:
            logger.error(f"❌ Ошибка инициализации фоновых рабочих: {e}")
            self.worker_manager = None

    def set_parent_manager(self, manager):
        """Устанавливает ссылку на родительский менеджер"""
        self.parent_manager = manager

    def _create_scroll_area(self, layout):
        """Создает скроллируемую область"""
        self.scroll_area = QScrollArea()
        self.scroll_area.setObjectName("InviterScroll")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # Контейнер для профилей
        self.profiles_container = QWidget()
        self.profiles_layout = QVBoxLayout(self.profiles_container)
        self.profiles_layout.setContentsMargins(10, 10, 10, 10)
        self.profiles_layout.setSpacing(8)

        self.scroll_area.setWidget(self.profiles_container)
        layout.addWidget(self.scroll_area)

        # Стили скролл бара
        self.scroll_area.setStyleSheet("""
            QScrollArea#InviterScroll {
                background: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background: rgba(255, 255, 255, 0.05);
                width: 8px;
                border-radius: 4px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 0.2);
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(59, 130, 246, 0.6);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

    def _load_profiles_from_module(self):
        """Загружает реальные профили из модуля"""
        try:
            from src.modules.impl.inviter import get_all_profiles_for_gui
            from src.modules.impl.inviter.profile_manager import InviterProfileManager

            profile_manager = InviterProfileManager()
            profile_manager.load_all_profiles()

            profiles_data = get_all_profiles_for_gui()

            logger.info(f"📨 Загружено реальных профилей из модуля: {len(profiles_data)}")

            if not profiles_data:
                self._show_empty_state()
                return

            # Загружаем профили
            for i, profile_data in enumerate(profiles_data):
                # ИСПОЛЬЗУЕМ ОПТИМИЗИРОВАННУЮ версию
                row = OptimizedInviterProfileRow(profile_data)

                # Подключаем сигналы после создания строки
                row.profile_started.connect(self._on_profile_started)
                row.profile_stopped.connect(self._on_profile_stopped)
                row.profile_deleted.connect(self._on_profile_deleted)

                # Добавляем в словарь для отслеживания
                self.profile_rows[profile_data['name']] = row
                self.profiles_layout.addWidget(row)

                # Добавляем разделитель сразу после строки
                if i < len(profiles_data) - 1:
                    sep = QFrame()
                    sep.setFrameShape(QFrame.HLine)
                    sep.setFrameShadow(QFrame.Sunken)
                    sep.setStyleSheet("color: rgba(255,255,255,0.1);")
                    sep.setFixedHeight(1)
                    self.profiles_layout.addWidget(sep)

            self.profiles_layout.addStretch()

        except Exception as e:
            logger.error(f"❌ Ошибка загрузки профилей из модуля: {e}")
            self._show_error_state(str(e))

    def _show_empty_state(self):
        """Показывает заглушку когда нет профилей"""
        empty_widget = QWidget()
        empty_layout = QVBoxLayout(empty_widget)
        empty_layout.setAlignment(Qt.AlignCenter)
        empty_layout.setSpacing(20)

        # Главная иконка и текст
        empty_label = QLabel("📭 Нет созданных профилей")
        empty_label.setAlignment(Qt.AlignCenter)
        empty_label.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 0.6);
                font-size: 24px;
                font-weight: 600;
                margin-bottom: 10px;
            }
        """)

        # Описание
        desc_label = QLabel("Создайте первый профиль для начала работы с инвайтером")
        desc_label.setAlignment(Qt.AlignCenter)
        desc_label.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 0.4);
                font-size: 16px;
                margin-bottom: 20px;
            }
        """)

        # Кнопка создания профиля
        create_btn = QPushButton("+ Создать первый профиль")
        create_btn.setFixedSize(200, 50)
        create_btn.setStyleSheet("""
            QPushButton {
                background: #22C55E;
                border: none;
                border-radius: 8px;
                color: #FFFFFF;
                font-size: 16px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #16A34A;
            }
            QPushButton:pressed {
                background: #15803D;
            }
        """)
        create_btn.clicked.connect(self._create_first_profile)

        # Контейнер для центрирования
        container = QWidget()
        container.setStyleSheet("""
            QWidget {
                background: rgba(255, 255, 255, 0.05);
                border-radius: 12px;
                border: 2px dashed rgba(255, 255, 255, 0.2);
                padding: 40px;
            }
        """)
        container_layout = QVBoxLayout(container)
        container_layout.addWidget(empty_label)
        container_layout.addWidget(desc_label)
        container_layout.addWidget(create_btn, 0, Qt.AlignCenter)

        empty_layout.addWidget(container)
        self.profiles_layout.addWidget(empty_widget)
        self.profiles_layout.addStretch()

    def _create_first_profile(self):
        """Создает первый профиль"""
        try:
            from gui.dialogs.inviter_dialogs import show_create_profile_dialog
            from src.modules.impl.inviter import create_profile

            profile_data = show_create_profile_dialog(self)

            if profile_data and profile_data.get('name'):
                profile_name = profile_data['name']
                logger.info(f"📨 Создаем первый профиль: {profile_name}")

                result = create_profile(profile_name, profile_data)

                if result.get('success'):
                    logger.info(f"✅ Первый профиль создан: {profile_name}")

                    self.reload_profiles()

                    if hasattr(self, 'parent_manager') and self.parent_manager:
                        self.parent_manager._reload_all_data()

                    try:
                        from gui.notifications import show_success
                        show_success(
                            "Профиль создан",
                            f"✅ Профиль '{profile_name}' успешно создан!\n"
                            f"Теперь вы можете настроить админов и токены."
                        )
                    except:
                        pass
                else:
                    logger.error(f"❌ Ошибка создания профиля: {result.get('message')}")

        except Exception as e:
            logger.error(f"❌ Ошибка создания первого профиля: {e}")

    def _show_error_state(self, error_message: str):
        """Показывает заглушку при ошибке загрузки"""
        error_label = QLabel(f"❌ Ошибка загрузки профилей\n\n{error_message}")
        error_label.setAlignment(Qt.AlignCenter)
        error_label.setStyleSheet("""
            QLabel {
                color: #EF4444;
                font-size: 14px;
                padding: 30px;
                background: rgba(239, 68, 68, 0.1);
                border-radius: 12px;
                border: 1px solid rgba(239, 68, 68, 0.3);
            }
        """)
        self.profiles_layout.addWidget(error_label)
        self.profiles_layout.addStretch()

    def _on_profile_started(self, profile_name):
        """ОПТИМИЗИРОВАННЫЙ запуск профиля - БЕЗ БЛОКИРОВКИ GUI"""
        logger.info(f"🚀 Запуск профиля: {profile_name}")

        # СРАЗУ меняем кнопку на "Стоп"
        if profile_name in self.profile_rows:
            profile_row = self.profile_rows[profile_name]
            profile_row.manually_stopped = False
            profile_row.update_running_state(True)

        # Запускаем в фоне БЕЗ БЛОКИРОВКИ
        import threading
        def start_task():
            try:
                from src.modules.impl.inviter import start_profile
                success = start_profile(profile_name)

                # Если запуск не удался - возвращаем кнопку
                if not success and profile_name in self.profile_rows:
                    QTimer.singleShot(100, lambda: self._reset_button_on_error(profile_name))

            except Exception as e:
                logger.error(f"❌ Ошибка запуска: {e}")
                QTimer.singleShot(100, lambda: self._reset_button_on_error(profile_name))

        # Запускаем в отдельном потоке
        thread = threading.Thread(target=start_task, daemon=True)
        thread.start()

    def _reset_button_on_error(self, profile_name):
        """Сбрасывает кнопку при ошибке запуска"""
        if profile_name in self.profile_rows:
            self.profile_rows[profile_name].update_running_state(False)
            if hasattr(self.profile_rows[profile_name], 'status_label'):
                self.profile_rows[profile_name].status_label.setText("❌ Ошибка запуска")

    def _on_profile_stopped(self, profile_name):
        """ОПТИМИЗИРОВАННАЯ остановка профиля - БЕЗ БЛОКИРОВКИ GUI"""
        logger.info(f"⏸️ Ручная остановка профиля: {profile_name}")

        # Помечаем как ручную остановку ПЕРЕД изменением UI
        if profile_name in self.profile_rows:
            profile_row = self.profile_rows[profile_name]
            profile_row.manually_stopped = True
            profile_row.update_running_state(False)

        # Останавливаем в фоне БЕЗ БЛОКИРОВКИ
        import threading
        def stop_task():
            try:
                from src.modules.impl.inviter import stop_profile
                result = stop_profile(profile_name)
                logger.info(f"⏹️ Результат остановки {profile_name}: {result}")
            except Exception as e:
                logger.error(f"❌ Ошибка остановки: {e}")

        thread = threading.Thread(target=stop_task, daemon=True)
        thread.start()

    def _on_profile_deleted(self, profile_name):
        """Обработка удаления профиля"""
        logger.info(f"🗑️ Удаление профиля: {profile_name}")

        try:
            from src.modules.impl.inviter import delete_profile
            result = delete_profile(profile_name)

            if result.get('success'):
                logger.info(f"✅ Профиль {profile_name} успешно удален через модуль")
                self.remove_profile(profile_name)
            else:
                logger.warning(f"⚠️ Не удалось удалить профиль {profile_name}: {result.get('message')}")
        except Exception as e:
            logger.error(f"❌ Ошибка удаления профиля {profile_name}: {e}")

    def add_profile(self, profile_data):
        """Добавляет новый профиль"""
        profile_name = profile_data.get('name')

        if profile_name in self.profile_rows:
            self.remove_profile(profile_name)

        # ИСПОЛЬЗУЕМ ОПТИМИЗИРОВАННУЮ версию
        profile_row = OptimizedInviterProfileRow(profile_data)

        profile_row.profile_started.connect(self._on_profile_started)
        profile_row.profile_stopped.connect(self._on_profile_stopped)
        profile_row.profile_deleted.connect(self._on_profile_deleted)

        self.profile_rows[profile_name] = profile_row
        self.profiles_layout.insertWidget(len(self.profile_rows) - 1, profile_row)

    def remove_profile(self, profile_name):
        """Удаляет профиль из интерфейса"""
        if profile_name in self.profile_rows:
            profile_row = self.profile_rows[profile_name]
            profile_row.deleteLater()
            del self.profile_rows[profile_name]
            logger.info(f"🗑️ Строка профиля {profile_name} удалена из интерфейса")

    def clear_profiles(self):
        """Очищает все профили"""
        for profile_row in self.profile_rows.values():
            profile_row.deleteLater()
        self.profile_rows.clear()
        logger.info("🧹 Все профили очищены из интерфейса")

    def start_all_profiles(self):
        """Запускает все профили БЕЗ БЛОКИРОВКИ"""
        for profile_row in self.profile_rows.values():
            if not profile_row.is_running:
                profile_row._toggle_profile()

    def stop_all_profiles(self):
        """Останавливает все профили БЕЗ БЛОКИРОВКИ"""
        for profile_row in self.profile_rows.values():
            if profile_row.is_running:
                profile_row._toggle_profile()

    def refresh_data(self):
        """ОПТИМИЗИРОВАННОЕ обновление данных профилей"""
        logger.info("🔄 ОПТИМИЗИРОВАННОЕ обновление данных профилей инвайтера...")

        try:
            # Просто перезагружаем профили - фоновые рабочие сами обновят статистики
            from src.modules.impl.inviter import get_all_profiles_for_gui

            profiles_data = get_all_profiles_for_gui()

            # БЫСТРОЕ обновление без блокировки
            self.clear_profiles()

            for profile_data in profiles_data:
                self.add_profile(profile_data)

            logger.info(f"✅ Данные профилей обновлены: {len(profiles_data)} профилей")

        except Exception as e:
            logger.error(f"❌ Ошибка обновления данных профилей: {e}")

    def reload_profiles(self):
        """ОПТИМИЗИРОВАННАЯ перезагрузка профилей"""
        try:
            self.clear_profiles()

            # Очищаем layout
            for i in reversed(range(self.profiles_layout.count())):
                item = self.profiles_layout.itemAt(i)
                if item.widget():
                    item.widget().deleteLater()

            self._load_profiles_from_module()

            logger.info("🔄 Профили перезагружены из модуля")

        except Exception as e:
            logger.error(f"❌ Ошибка перезагрузки профилей: {e}")

    def animate_appearance(self):
        """Анимирует появление таблицы"""
        effect = self.graphicsEffect()
        if effect:
            self.opacity_animation = QPropertyAnimation(effect, b"opacity")
            self.opacity_animation.setDuration(800)
            self.opacity_animation.setStartValue(0.0)
            self.opacity_animation.setEndValue(1.0)
            self.opacity_animation.setEasingCurve(QEasingCurve.OutCubic)
            self.opacity_animation.start()

    def __del__(self):
        """Деструктор - останавливаем фоновых рабочих"""
        try:
            if hasattr(self, 'worker_manager') and self.worker_manager:
                from gui.workers.background_workers import shutdown_worker_manager
                shutdown_worker_manager()
        except:
            pass