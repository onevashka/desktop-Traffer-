# gui/component_inviter/inviter_table.py - ИСПРАВЛЕННАЯ ВЕРСИЯ
"""
Компонент таблицы профилей инвайтера с исправленным выбором ботов
"""

from gui.dialogs.inviter_dialogs import (
    show_users_base_dialog,
    show_chats_base_dialog,
    show_extended_settings_dialog
)
from gui.dialogs.bot_holders_dialog import show_bot_holders_dialog

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QFrame,
    QLabel, QPushButton, QComboBox, QSpinBox, QCheckBox,
    QProgressBar, QSizePolicy, QGraphicsOpacityEffect, QLineEdit
)
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, Signal

from PySide6.QtGui import QFont, QColor
from loguru import logger
from typing import Optional, Dict


class InviterProfileRow(QWidget):
    """Двухэтажная строка профиля инвайтера с исправленным управлением ботами"""

    # Сигналы
    profile_started = Signal(str)  # profile_name
    profile_stopped = Signal(str)  # profile_name
    profile_deleted = Signal(str)  # profile_name
    settings_changed = Signal(str, dict)  # profile_name, settings

    def __init__(self, profile_data):
        super().__init__()
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.profile_data = profile_data
        self.profile_name = profile_data.get('name', 'Профиль')
        self.is_running = profile_data.get('is_running', False)

        self.users_list = profile_data.get('users_list', [])
        self.chats_list = profile_data.get('chats_list', [])
        self.extended_settings = profile_data.get('extended_settings', {})

        # Статистика процесса для прогресс-бара
        self.process_stats = profile_data.get('process_stats', {})

        # Сохраненные данные прогресса (чтобы не терять при остановке)
        self.saved_progress = {
            'success': 0,
            'errors': 0,
            'total_goal': 0,
            'stop_reason': None
        }

        # ВАЖНО: Инициализируем bot_account СРАЗУ в начале
        self.bot_account = profile_data.get('bot_account', None)
        if not self.bot_account and profile_data.get('config', {}).get('bot_account'):
            self.bot_account = profile_data['config']['bot_account']

        # Таймер для обновления прогресс-бара
        self.progress_timer = QTimer()
        self.progress_timer.timeout.connect(self._update_progress_from_module)

        # Таймер для проверки завершения процесса
        self.completion_timer = QTimer()
        self.completion_timer.timeout.connect(self._check_process_completion)

        self.setObjectName("InviterProfileRow")
        self.setFixedHeight(140)  # Двухэтажная высота

        # Инициализируем кнопки как None
        self.users_btn = None
        self.chats_btn = None
        self.settings_btn = None
        self.delete_btn = None
        self.start_stop_btn = None
        self.name_edit = None
        self.invite_type_combo = None
        self.bot_select_btn = None  # НОВАЯ КНОПКА

        # Основной layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 10, 15, 10)
        main_layout.setSpacing(8)

        # Первый этаж - основные настройки
        self._create_first_floor(main_layout)

        # Второй этаж - счетчики и прогресс
        self._create_second_floor(main_layout)

        # Стили
        self._apply_styles()

        # Подключаем обработчики ПОСЛЕ создания всех кнопок
        self._connect_signals()

        # Запускаем обновление прогресса если профиль запущен
        if self.is_running:
            self.progress_timer.start(1000)  # Обновляем каждую секунду
            self.completion_timer.start(2000)  # Проверяем завершение каждые 2 секунды

    def _connect_signals(self):
        """Подключает все сигналы к кнопкам"""
        try:
            if self.users_btn:
                self.users_btn.clicked.connect(self._on_users_settings)
                logger.debug(f"✅ Подключен сигнал users_btn для {self.profile_name}")

            if self.chats_btn:
                self.chats_btn.clicked.connect(self._on_chats_settings)
                logger.debug(f"✅ Подключен сигнал chats_btn для {self.profile_name}")

            if self.settings_btn:
                self.settings_btn.clicked.connect(self._on_extended_settings)
                logger.debug(f"✅ Подключен сигнал settings_btn для {self.profile_name}")

            if self.delete_btn:
                self.delete_btn.clicked.connect(self._delete_profile)
                logger.debug(f"✅ Подключен сигнал delete_btn для {self.profile_name}")

            if self.start_stop_btn:
                self.start_stop_btn.clicked.connect(self._toggle_profile)
                logger.debug(f"✅ Подключен сигнал start_stop_btn для {self.profile_name}")

            if self.name_edit:
                self.name_edit.textChanged.connect(self._on_name_changed)
                logger.debug(f"✅ Подключен сигнал name_edit для {self.profile_name}")

            # ИСПРАВЛЕНО: Подключаем сигнал смены типа инвайта БЕЗ автоматического диалога
            if self.invite_type_combo:
                self.invite_type_combo.currentTextChanged.connect(self._on_invite_type_changed_simple)
                logger.debug(f"✅ Подключен сигнал invite_type_combo для {self.profile_name}")

            # НОВОЕ: Подключаем кнопку выбора бота
            if self.bot_select_btn:
                self.bot_select_btn.clicked.connect(self._on_select_bot_account)
                logger.debug(f"✅ Подключен сигнал bot_select_btn для {self.profile_name}")

        except Exception as e:
            logger.error(f"❌ Ошибка подключения сигналов для {self.profile_name}: {e}")

    def _create_first_floor(self, main_layout):
        """Создает первый этаж с основными настройками"""
        first_floor = QWidget()
        first_floor.setObjectName("FirstFloor")  # Добавляем ObjectName для поиска
        layout = QHBoxLayout(first_floor)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # 1. Индикатор статуса и кнопка запуска
        layout.addWidget(self._create_status_widget())
        layout.addWidget(self._create_start_button_widget())

        # 2. Название профиля
        layout.addWidget(self._create_name_widget())

        # 3. Тип инвайта + кнопка выбора бота
        layout.addWidget(self._create_invite_type_widget())

        # 4. База пользователей
        layout.addWidget(self._create_users_base_widget())

        # 5. База чатов
        layout.addWidget(self._create_chats_base_widget())

        # 6. Кнопки управления
        self.control_buttons_widget = self._create_control_buttons()
        layout.addWidget(self.control_buttons_widget)

        main_layout.addWidget(first_floor)

    def _create_invite_type_widget(self):
        """ИСПРАВЛЕНО: Тип инвайта + кнопка выбора бота"""
        widget = QWidget()
        widget.setFixedWidth(280)  # Увеличили ширину для кнопки
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Заголовок
        type_label = QLabel("Тип инвайта:")
        type_label.setStyleSheet("font-size: 12px; color: rgba(255,255,255,0.6);")

        # Горизонтальный layout для комбобокса и кнопки
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(6)

        # Комбобокс типа инвайта
        self.invite_type_combo = QComboBox()
        self.invite_type_combo.addItems(["Классический", "Через админку"])
        self.invite_type_combo.setFixedWidth(140)
        self.invite_type_combo.setFixedHeight(28)
        self.invite_type_combo.setStyleSheet("""
            QComboBox {
                background: #111827;
                border: 1px solid #374151;
                border-radius: 4px;
                color: #FFFFFF;
                font-size: 13px;
                padding: 4px 8px;
            }
            QComboBox:focus {
                border-color: #2563EB;
            }
            QComboBox QAbstractItemView {
                background: #1F2937;
                border: 1px solid #374151;
                selection-background-color: #2563EB;
                color: #FFFFFF;
                font-size: 13px;
            }
        """)

        # Устанавливаем текущий тип
        current_type = self.profile_data.get('config', {}).get('invite_type', 'classic')
        if current_type == 'admin':
            self.invite_type_combo.setCurrentText("Через админку")
        else:
            self.invite_type_combo.setCurrentText("Классический")

        # НОВАЯ КНОПКА: Выбрать бота (показывается только для режима "Через админку")
        self.bot_select_btn = QPushButton("🤖 Выбрать бота")
        self.bot_select_btn.setFixedSize(120, 28)
        self.bot_select_btn.setStyleSheet("""
            QPushButton {
                background: rgba(59, 130, 246, 0.2);
                border: 1px solid rgba(59, 130, 246, 0.5);
                border-radius: 4px;
                color: #FFFFFF;
                font-size: 12px;
                font-weight: 600;
                padding: 0 8px;
            }
            QPushButton:hover {
                background: rgba(59, 130, 246, 0.3);
            }
            QPushButton:pressed {
                background: rgba(59, 130, 246, 0.4);
            }
        """)

        controls_layout.addWidget(self.invite_type_combo)
        controls_layout.addWidget(self.bot_select_btn)

        layout.addWidget(type_label)
        layout.addLayout(controls_layout)

        # Изначально скрываем кнопку если режим классический
        self._update_bot_button_visibility()

        return widget

    def _on_invite_type_changed_simple(self, new_type: str):
        """ИСПРАВЛЕНО: Простая смена типа без автоматического диалога"""
        try:
            logger.info(f"🔄 Изменен тип инвайта на: {new_type}")

            # Сохраняем тип в конфигурацию
            if new_type == "Через админку":
                self._save_invite_type_settings('admin', self.bot_account)
            else:
                self._save_invite_type_settings('classic', None)
                # При переключении на классический сбрасываем бота
                self.bot_account = None

            # Обновляем видимость кнопки
            self._update_bot_button_visibility()

            # Обновляем UI
            self._update_bot_info_display()

        except Exception as e:
            logger.error(f"❌ Ошибка изменения типа инвайта: {e}")

    def _on_select_bot_account(self):
        """НОВЫЙ МЕТОД: Обработчик кнопки выбора бота"""
        try:
            logger.info(f"🤖 Открываем диалог выбора бота для {self.profile_name}")

            # Показываем диалог выбора аккаунтов
            selected_accounts = show_bot_holders_dialog(self)

            if selected_accounts:
                # Берем первый выбранный аккаунт
                bot_account = selected_accounts[0]
                self.bot_account = bot_account

                # Сохраняем в конфигурацию
                self._save_invite_type_settings('admin', bot_account)

                # Показываем уведомление
                from gui.notifications import show_success
                show_success(
                    "Бот назначен",
                    f"🤖 Аккаунт {bot_account['name']} будет управлять ботом"
                )

                # Обновляем UI
                self._update_bot_info_display()

                logger.info(f"✅ Выбран бот-аккаунт: {bot_account['name']}")
            else:
                logger.info("❌ Выбор бота отменен")

        except Exception as e:
            logger.error(f"❌ Ошибка выбора бота: {e}")

    def _update_bot_button_visibility(self):
        """Обновляет видимость кнопки выбора бота"""
        if self.bot_select_btn and self.invite_type_combo:
            current_type = self.invite_type_combo.currentText()

            if current_type == "Через админку":
                self.bot_select_btn.setVisible(True)
                self.bot_select_btn.setEnabled(True)
            else:
                self.bot_select_btn.setVisible(False)

    def _save_invite_type_settings(self, invite_type: str, bot_account: Optional[Dict]):
        """Сохраняет настройки типа инвайта"""
        try:
            config_update = {
                'invite_type': invite_type
            }

            if bot_account:
                config_update['bot_account'] = {
                    'name': bot_account['name'],
                    'phone': bot_account.get('phone', ''),
                    'full_name': bot_account.get('full_name', '')
                }
            else:
                config_update['bot_account'] = None

            # Сохраняем через модуль
            from src.modules.impl.inviter import update_profile_config
            success = update_profile_config(self.profile_name, config_update)

            if success:
                # Обновляем локальные данные
                if 'config' not in self.profile_data:
                    self.profile_data['config'] = {}
                self.profile_data['config'].update(config_update)

                logger.info(f"✅ Настройки типа инвайта сохранены: {invite_type}")
            else:
                logger.error("❌ Не удалось сохранить настройки типа инвайта")

        except Exception as e:
            logger.error(f"❌ Ошибка сохранения настроек типа инвайта: {e}")

    def _update_bot_info_display(self):
        """Обновляет отображение информации о боте"""
        # Пересоздаем виджет кнопок управления с новой информацией
        if hasattr(self, 'control_buttons_widget'):
            # Находим старый виджет в layout
            first_floor_widget = self.findChild(QWidget, "FirstFloor")
            if first_floor_widget:
                layout = first_floor_widget.layout()
                if layout:
                    # Удаляем старый виджет
                    old_widget = self.control_buttons_widget
                    layout.removeWidget(old_widget)
                    old_widget.deleteLater()

                    # Создаем новый с обновленной информацией
                    self.control_buttons_widget = self._create_control_buttons()
                    layout.addWidget(self.control_buttons_widget)

        # Логируем информацию
        if self.bot_account:
            logger.info(f"🤖 Профиль использует бот: {self.bot_account['name']}")
        else:
            logger.info("📝 Профиль использует классический режим инвайта")

    def _create_name_widget(self):
        """Название профиля — редактируемое поле"""
        widget = QWidget()
        widget.setFixedWidth(200)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        name_label = QLabel("Профиль:")
        name_label.setStyleSheet("font-size: 12px; color: rgba(255,255,255,0.6);")

        self.name_edit = QLineEdit(self.profile_name)
        self.name_edit.setFixedWidth(180)
        self.name_edit.setFixedHeight(28)
        self.name_edit.setStyleSheet("""
            QLineEdit {
                background: #111827;
                border: 1px solid #374151;
                border-radius: 4px;
                color: #FFFFFF;
                font-size: 13px;
                padding: 4px;
            }
            QLineEdit:focus {
                border-color: #2563EB;
            }
        """)

        layout.addWidget(name_label)
        layout.addWidget(self.name_edit)
        return widget

    def _on_name_changed(self):
        """Обработчик изменения имени профиля"""
        if not self.name_edit:
            return

        new_name = self.name_edit.text().strip() or self.profile_name
        if new_name != self.profile_name:
            self.profile_name = new_name
            self.settings_changed.emit(self.profile_name, {'name': new_name})

    def _create_status_widget(self):
        """Индикатор статуса"""
        widget = QWidget()
        widget.setFixedWidth(80)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Индикатор статуса
        self.status_indicator = QLabel("●")
        self.status_indicator.setAlignment(Qt.AlignCenter)
        self.status_indicator.setStyleSheet(f"""
            QLabel {{
                font-size: 16px;
                color: {'#10B981' if self.is_running else '#6B7280'};
                font-weight: bold;
            }}
        """)

        layout.addWidget(self.status_indicator)

        return widget

    def _create_start_button_widget(self):
        """Кнопка Запустить/Стоп цветная."""
        widget = QWidget()
        widget.setFixedWidth(120)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignCenter)

        # Создаём кнопку и сохраняем ссылку
        self.start_stop_btn = QPushButton()
        self._update_start_button()  # задаст текст и цвет
        self.start_stop_btn.setFixedSize(100, 40)

        layout.addWidget(self.start_stop_btn)
        return widget

    def _update_start_button(self):
        """Обновляет текст и цвет кнопки в зависимости от состояния."""
        if not self.start_stop_btn:
            return

        if self.is_running:
            self.start_stop_btn.setText("Стоп")
            self.start_stop_btn.setStyleSheet("""
                QPushButton {
                    background: #EF4444;
                    color: white;
                    border-radius: 6px;
                    font-weight: 600;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background: #DC2626;
                }
                QPushButton:pressed {
                    background: #B91C1C;
                }
            """)
        else:
            self.start_stop_btn.setText("Запустить")
            self.start_stop_btn.setStyleSheet("""
                QPushButton {
                    background: #10B981;
                    color: white;
                    border-radius: 6px;
                    font-weight: 600;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background: #059669;
                }
                QPushButton:pressed {
                    background: #047857;
                }
            """)

    def _create_users_base_widget(self):
        """База пользователей с улучшенным отображением"""
        widget = QWidget()
        widget.setFixedWidth(120)  # Увеличили ширину
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        users_count = len(self.users_list)

        # Форматируем большие числа
        if users_count >= 1000000:
            button_text = f"👥 {users_count // 1000000}.{(users_count % 1000000) // 100000}M"
        elif users_count >= 1000:
            button_text = f"👥 {users_count // 1000}K"
        else:
            button_text = f"👥 {users_count}"

        self.users_btn = QPushButton(button_text)
        self.users_btn.setFixedHeight(30)  # Увеличили высоту
        self.users_btn.setToolTip(f"Всего пользователей: {users_count:,}")  # Показываем полное число в подсказке
        self.users_btn.setStyleSheet("""
            QPushButton {
                background: rgba(59, 130, 246, 0.2);
                border: 1px solid rgba(59, 130, 246, 0.5);
                border-radius: 4px;
                color: #FFFFFF;
                font-size: 13px;
                font-weight: 600;
                padding: 0 8px;
            }
            QPushButton:hover {
                background: rgba(59, 130, 246, 0.3);
            }
        """)

        layout.addWidget(self.users_btn)
        return widget

    def _create_chats_base_widget(self):
        """База чатов с улучшенным отображением"""
        widget = QWidget()
        widget.setFixedWidth(120)  # Увеличили ширину
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        chats_count = len(self.chats_list)

        # Форматируем большие числа
        if chats_count >= 1000:
            button_text = f"💬 {chats_count // 1000}K"
        else:
            button_text = f"💬 {chats_count}"

        self.chats_btn = QPushButton(button_text)
        self.chats_btn.setFixedHeight(30)  # Увеличили высоту
        self.chats_btn.setToolTip(f"Всего чатов: {chats_count:,}")  # Показываем полное число в подсказке
        self.chats_btn.setStyleSheet("""
            QPushButton {
                background: rgba(16, 185, 129, 0.2);
                border: 1px solid rgba(16, 185, 129, 0.5);
                border-radius: 4px;
                color: #FFFFFF;
                font-size: 13px;
                font-weight: 600;
                padding: 0 8px;
            }
            QPushButton:hover {
                background: rgba(16, 185, 129, 0.3);
            }
        """)

        layout.addWidget(self.chats_btn)
        return widget

    def _create_control_buttons(self):
        """Кнопки управления профилем"""
        widget = QWidget()
        widget.setFixedWidth(200)  # Увеличили ширину для информации о боте
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Информация о боте (если есть)
        if self.bot_account:
            bot_info = QLabel(f"🤖 {self.bot_account.get('name', 'Bot')}")
            bot_info.setToolTip(f"Управляется ботом: {self.bot_account.get('name', '')}")
            bot_info.setStyleSheet("""
                   QLabel {
                       background: rgba(59, 130, 246, 0.1);
                       border: 1px solid rgba(59, 130, 246, 0.3);
                       border-radius: 4px;
                       padding: 4px 8px;
                       color: #3B82F6;
                       font-size: 11px;
                       font-weight: 600;
                   }
               """)
            layout.addWidget(bot_info)
            layout.addStretch()

        # Кнопка настроек
        self.settings_btn = QPushButton("⚙️")
        self.settings_btn.setFixedSize(36, 36)
        self.settings_btn.setToolTip("Расширенные настройки")
        self.settings_btn.setStyleSheet("""
               QPushButton {
                   background: rgba(156, 163, 175, 0.2);
                   border: 1px solid rgba(156, 163, 175, 0.5);
                   border-radius: 4px;
                   color: #FFFFFF;
                   font-size: 12px;
               }
               QPushButton:hover {
                   background: rgba(156, 163, 175, 0.3);
               }
           """)

        # Кнопка удаления
        self.delete_btn = QPushButton("🗑️")
        self.delete_btn.setFixedSize(36, 36)
        self.delete_btn.setToolTip("Удалить профиль")
        self.delete_btn.setStyleSheet("""
               QPushButton {
                   background: rgba(239, 68, 68, 0.2);
                   border: 1px solid rgba(239, 68, 68, 0.5);
                   border-radius: 4px;
                   color: #FFFFFF;
                   font-size: 12px;
               }
               QPushButton:hover {
                   background: rgba(239, 68, 68, 0.3);
               }
           """)

        layout.addWidget(self.settings_btn)
        layout.addWidget(self.delete_btn)

        return widget

    # Остальные методы остаются без изменений
    def _create_second_floor(self, main_layout):
        """Второй этаж с прогресс-баром и статистикой"""
        second_floor = QWidget()
        layout = QVBoxLayout(second_floor)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        # Прогресс-бар
        progress_widget = self._create_progress_widget()
        progress_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout.addWidget(progress_widget)

        # Дополнительная статистика
        stats_widget = self._create_stats_widget()
        layout.addWidget(stats_widget)

        main_layout.addWidget(second_floor)

    def _create_progress_widget(self):
        """Создает виджет с прогресс-баром"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        progress_label = QLabel("Прогресс инвайтов:")
        progress_label.setStyleSheet("font-size: 11px; color: rgba(255,255,255,0.6);")

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(24)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%v из %m (%p%)")

        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 8px;
                background: rgba(255, 255, 255, 0.1);
                text-align: center;
                color: #FFFFFF;
                font-size: 10px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3B82F6, stop:1 #8B5CF6);
                border-radius: 8px;
            }
        """)

        layout.addWidget(progress_label)
        layout.addWidget(self.progress_bar)

        return widget

    def _create_stats_widget(self):
        """Создает виджет со статистикой"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(20)

        # Статус
        self.status_label = QLabel("Ожидание...")
        self.status_label.setStyleSheet("font-size: 11px; color: rgba(255,255,255,0.7);")

        # Счетчики
        self.success_label = QLabel("✅ Успешно: 0")
        self.success_label.setStyleSheet("font-size: 11px; color: #10B981;")

        self.errors_label = QLabel("❌ Ошибок: 0")
        self.errors_label.setStyleSheet("font-size: 11px; color: #EF4444;")

        self.speed_label = QLabel("⚡ Скорость: 0/мин")
        self.speed_label.setStyleSheet("font-size: 11px; color: #F59E0B;")

        layout.addWidget(self.status_label)
        layout.addStretch()
        layout.addWidget(self.success_label)
        layout.addWidget(self.errors_label)
        layout.addWidget(self.speed_label)

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

    def _toggle_profile(self):
        """Переключает состояние профиля"""
        if self.is_running:
            # Останавливаем
            self.profile_stopped.emit(self.profile_name)
        else:
            # Запускаем
            self.profile_started.emit(self.profile_name)

    def update_running_state(self, is_running: bool):
        """Обновляет состояние запуска профиля"""
        self.is_running = is_running

        # Обновляем индикатор
        self.status_indicator.setStyleSheet(f"""
            QLabel {{
                font-size: 16px;
                color: {'#10B981' if self.is_running else '#6B7280'};
                font-weight: bold;
            }}
        """)

        # Обновляем кнопку
        self._update_start_button()

        # Управляем таймерами
        if self.is_running:
            self.progress_timer.start(1000)  # Обновляем каждую секунду
            self.completion_timer.start(2000)  # Проверяем завершение
            self.status_label.setText("Запущен...")
        else:
            self.progress_timer.stop()
            self.completion_timer.stop()
            # НЕ сбрасываем прогресс при остановке!
            # self.progress_bar.setValue(0)

    def _update_progress_from_module(self):
        """Обновляет прогресс-бар из данных модуля"""
        try:
            # Получаем актуальные данные из модуля
            from src.modules.impl.inviter import get_profile_progress

            progress_data = get_profile_progress(self.profile_name)

            if progress_data:
                # Обновляем прогресс-бар относительно ЦЕЛИ
                total_goal = progress_data.get('total_goal', 0)
                success = progress_data.get('success', 0)
                errors = progress_data.get('errors', 0)

                # Сохраняем данные прогресса
                self.saved_progress['success'] = success
                self.saved_progress['errors'] = errors
                self.saved_progress['total_goal'] = total_goal

                if total_goal > 0:
                    # Прогресс-бар показывает успешные инвайты относительно цели
                    self.progress_bar.setRange(0, total_goal)
                    self.progress_bar.setValue(success)
                    self.progress_bar.setFormat(
                        f"{success} из {total_goal} ({success * 100 // total_goal if total_goal > 0 else 0}%)")

                    # Обновляем счетчики
                    self.success_label.setText(f"✅ Успешно: {success}")
                    self.errors_label.setText(f"❌ Ошибок: {errors}")

                    # Рассчитываем скорость
                    speed = progress_data.get('speed', 0)
                    self.speed_label.setText(f"⚡ Скорость: {speed}/мин")

                    # Обновляем статус
                    status = progress_data.get('status', 'Работает...')
                    active_accounts = progress_data.get('active_accounts', 0)
                    finished_accounts = progress_data.get('finished_accounts', 0)

                    # Добавляем информацию об аккаунтах в статус
                    if finished_accounts > 0:
                        status += f" | Отработало: {finished_accounts} акк."

                    self.status_label.setText(status)

                    # Если цель достигнута
                    if success >= total_goal:
                        self.status_label.setText("✅ Цель достигнута!")
                        self.saved_progress['stop_reason'] = "Цель достигнута"
                        self.progress_bar.setStyleSheet("""
                            QProgressBar {
                                border: 1px solid rgba(16, 185, 129, 0.5);
                                border-radius: 8px;
                                background: rgba(16, 185, 129, 0.1);
                                text-align: center;
                                color: #FFFFFF;
                                font-size: 10px;
                            }
                            QProgressBar::chunk {
                                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                    stop:0 #10B981, stop:1 #059669);
                                border-radius: 8px;
                            }
                        """)
                else:
                    # Если цель не определена, показываем количество обработанных
                    processed = progress_data.get('processed', 0)
                    self.progress_bar.setRange(0, 100)
                    self.progress_bar.setValue(min(processed, 100))
                    self.progress_bar.setFormat(f"Обработано: {processed}")
            else:
                # Процесс завершен, используем сохраненные данные
                if self.saved_progress['total_goal'] > 0:
                    success = self.saved_progress['success']
                    total_goal = self.saved_progress['total_goal']

                    # Показываем финальный статус
                    if self.saved_progress['stop_reason']:
                        self.status_label.setText(f"⏹️ Остановлен: {self.saved_progress['stop_reason']}")
                    else:
                        self.status_label.setText("⏹️ Остановлен пользователем")

        except Exception as e:
            logger.error(f"❌ Ошибка обновления прогресса для {self.profile_name}: {e}")

    def _check_process_completion(self):
        """Проверяет завершился ли процесс и автоматически меняет кнопку"""
        try:
            from src.modules.impl.inviter import get_profile_progress

            progress_data = get_profile_progress(self.profile_name)

            if not progress_data or not progress_data.get('is_running', False):
                # Процесс завершен
                if self.is_running:
                    logger.info(f"🏁 Процесс {self.profile_name} завершен, обновляем UI")

                    # Определяем причину остановки
                    if self.saved_progress.get('success', 0) >= self.saved_progress.get('total_goal', 1):
                        self.saved_progress['stop_reason'] = "✅ Цель достигнута"
                    elif not self.saved_progress.get('stop_reason'):
                        # Пытаемся определить причину из последних данных
                        if progress_data:
                            status = progress_data.get('status', '')
                            if 'завершен' in status.lower():
                                self.saved_progress['stop_reason'] = "Работа завершена"
                            elif 'ошибк' in status.lower():
                                self.saved_progress['stop_reason'] = "Остановлен из-за ошибок"
                            elif 'нет аккаунтов' in status.lower():
                                self.saved_progress['stop_reason'] = "Нет доступных аккаунтов"
                            elif 'нет пользователей' in status.lower():
                                self.saved_progress['stop_reason'] = "Закончились пользователи"
                            else:
                                self.saved_progress['stop_reason'] = "Процесс завершен"

                    # Автоматически переключаем состояние на остановленное
                    self.update_running_state(False)

                    # Обновляем финальный статус
                    if self.saved_progress['stop_reason']:
                        self.status_label.setText(f"⏹️ {self.saved_progress['stop_reason']}")

        except Exception as e:
            logger.error(f"❌ Ошибка проверки завершения для {self.profile_name}: {e}")

    def _delete_profile(self):
        """Удаляет профиль"""
        self.profile_deleted.emit(self.profile_name)

    def _on_users_settings(self):
        """Настройка базы пользователей"""
        try:
            logger.info(f"🔧 Открываем настройки пользователей для профиля: {self.profile_name}")

            current_users = getattr(self, 'users_list', [])
            users = show_users_base_dialog(self, current_users)

            if users is not None:
                logger.info(f"📥 Получено пользователей из диалога: {len(users)}")

                # Импортируем модуль
                from src.modules.impl.inviter import update_profile_users

                # Сохраняем в модуле
                success = update_profile_users(self.profile_name, users)

                if success:
                    self.users_list = users
                    users_count = len(users)

                    # Форматируем большие числа
                    if users_count >= 1000000:
                        button_text = f"👥 {users_count // 1000000}.{(users_count % 1000000) // 100000}M"
                    elif users_count >= 1000:
                        button_text = f"👥 {users_count // 1000}K"
                    else:
                        button_text = f"👥 {users_count}"

                    if self.users_btn:
                        self.users_btn.setText(button_text)
                        self.users_btn.setToolTip(f"Всего пользователей: {users_count:,}")

                    logger.info(f"✅ База пользователей обновлена для {self.profile_name}: {users_count} пользователей")

                    # Показываем уведомление об успехе
                    try:
                        from gui.notifications import show_success
                        show_success(
                            "База пользователей",
                            f"✅ Сохранено {users_count:,} пользователей\nВ файл: База юзеров.txt"
                        )
                    except:
                        pass

                else:
                    logger.error(f"❌ Не удалось сохранить пользователей для {self.profile_name}")
                    try:
                        from gui.notifications import show_error
                        show_error(
                            "Ошибка сохранения",
                            "❌ Не удалось сохранить пользователей в файл"
                        )
                    except:
                        pass

        except Exception as e:
            logger.error(f"❌ Ошибка настройки пользователей: {e}")

    def _on_chats_settings(self):
        """Настройка базы чатов"""
        try:
            logger.info(f"🔧 Открываем настройки чатов для профиля: {self.profile_name}")

            current_chats = getattr(self, 'chats_list', [])
            chats = show_chats_base_dialog(self, current_chats)

            if chats is not None:
                logger.info(f"📥 Получено чатов из диалога: {len(chats)}")

                # Импортируем модуль
                from src.modules.impl.inviter import update_profile_chats

                # Сохраняем в модуле
                success = update_profile_chats(self.profile_name, chats)

                if success:
                    self.chats_list = chats
                    chats_count = len(chats)

                    # Форматируем большие числа
                    if chats_count >= 1000:
                        button_text = f"💬 {chats_count // 1000}K"
                    else:
                        button_text = f"💬 {chats_count}"

                    if self.chats_btn:
                        self.chats_btn.setText(button_text)
                        self.chats_btn.setToolTip(f"Всего чатов: {chats_count:,}")

                    logger.info(f"✅ База чатов обновлена для {self.profile_name}: {chats_count} чатов")

                    # Показываем уведомление об успехе
                    try:
                        from gui.notifications import show_success
                        show_success(
                            "База чатов",
                            f"✅ Сохранено {chats_count:,} чатов\nВ файл: База чатов.txt"
                        )
                    except:
                        pass

                else:
                    logger.error(f"❌ Не удалось сохранить чаты для {self.profile_name}")
                    try:
                        from gui.notifications import show_error
                        show_error(
                            "Ошибка сохранения",
                            "❌ Не удалось сохранить чаты в файл"
                        )
                    except:
                        pass

        except Exception as e:
            logger.error(f"❌ Ошибка настройки чатов: {e}")

    def _on_extended_settings(self):
        """Расширенные настройки профиля"""
        try:
            from src.modules.impl.inviter.inviter_manager import _inviter_module_manager

            if _inviter_module_manager:
                fresh_profile = _inviter_module_manager.profile_manager.get_profile(self.profile_name)
                if fresh_profile:
                    current_config = fresh_profile.get('config', {})
                else:
                    current_config = self.profile_data.get('config', {})
            else:
                current_config = self.profile_data.get('config', {})

            logger.debug(f"📝 Загружаем настройки для {self.profile_name}: {current_config}")

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
            else:
                logger.error(f"❌ Не удалось сохранить настройки в модуль")
                try:
                    from gui.notifications import show_error
                    show_error(
                        "Ошибка сохранения",
                        "Не удалось сохранить настройки в модуль"
                    )
                except:
                    pass

        except Exception as e:
            logger.error(f"❌ Ошибка сохранения настроек в модуль: {e}")

    def update_progress(self, done: int, total: int):
        """Обновляем прогресс-бар напрямую"""
        if self.progress_bar:
            self.progress_bar.setRange(0, total)
            self.progress_bar.setValue(done)

    def update_counters(self, success, errors, total):
        """Обновляет счетчики"""
        if hasattr(self, 'success_label'):
            self.success_label.setText(f"✅ Успешно: {success}")
        if hasattr(self, 'errors_label'):
            self.errors_label.setText(f"❌ Ошибок: {errors}")

    def update_last_action(self, action_text):
        """Обновляет текст последнего действия"""
        if hasattr(self, 'status_label'):
            self.status_label.setText(action_text)


class InviterTableWidget(QWidget):
    """Основная таблица с профилями инвайтера"""

    def __init__(self):
        super().__init__()
        self.setObjectName("InviterTableWidget")

        # Список строк профилей для отслеживания
        self.profile_rows = {}  # Словарь для быстрого доступа

        # Основной layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Создаем скролл область
        self._create_scroll_area(layout)

        # Загружаем тестовые данные
        self._load_test_profiles()

        # Эффект прозрачности для анимации
        effect = QGraphicsOpacityEffect()
        effect.setOpacity(0.0)
        self.setGraphicsEffect(effect)

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

    # Остальные методы класса остаются без изменений...
    def _load_test_profiles(self):
        """Загружает тестовые профили"""
        test_profiles = [
            {
                'name': 'Профиль #1',
                'is_running': False,
                'invite_type': 'Классический',
                'threads': 2,
                'chat_limit': 50,
                'acc_limit': 100,
                'users_list': [],
                'chats_list': [],
                'extended_settings': {}
            },
            {
                'name': 'Профиль #2',
                'is_running': True,
                'invite_type': 'Через админку',
                'threads': 3,
                'chat_limit': 75,
                'acc_limit': 150,
                'users_list': [],
                'chats_list': [],
                'extended_settings': {}
            },
            {
                'name': 'Профиль #3',
                'is_running': False,
                'invite_type': 'Классический',
                'threads': 1,
                'chat_limit': 30,
                'acc_limit': 80,
                'users_list': [],
                'chats_list': [],
                'extended_settings': {}
            }
        ]

        for i, data in enumerate(test_profiles):
            row = InviterProfileRow(data)

            # Подключаем сигналы после создания строки
            row.profile_started.connect(self._on_profile_started)
            row.profile_stopped.connect(self._on_profile_stopped)
            row.profile_deleted.connect(self._on_profile_deleted)

            # Добавляем в словарь для отслеживания
            self.profile_rows[data['name']] = row
            self.profiles_layout.addWidget(row)

            # Добавляем разделитель сразу после строки
            if i < len(test_profiles) - 1:
                sep = QFrame()
                sep.setFrameShape(QFrame.HLine)
                sep.setFrameShadow(QFrame.Sunken)
                sep.setStyleSheet("color: rgba(255,255,255,0.1);")
                sep.setFixedHeight(1)
                self.profiles_layout.addWidget(sep)

        self.profiles_layout.addStretch()

    def _on_profile_started(self, profile_name):
        """Обработка запуска профиля"""
        logger.info(f"🚀 Профиль запущен: {profile_name}")

        try:
            from src.modules.impl.inviter import start_profile
            success = start_profile(profile_name)

            # Обновляем состояние строки
            if profile_name in self.profile_rows:
                self.profile_rows[profile_name].update_running_state(success)

            if success:
                logger.info(f"✅ Профиль {profile_name} успешно запущен через модуль")
            else:
                logger.warning(f"⚠️ Не удалось запустить профиль {profile_name} через модуль")
        except Exception as e:
            logger.error(f"❌ Ошибка запуска профиля {profile_name}: {e}")

    def _on_profile_stopped(self, profile_name):
        """Обработка остановки профиля"""
        logger.info(f"⏸️ Профиль остановлен: {profile_name}")

        try:
            from src.modules.impl.inviter import stop_profile
            success = stop_profile(profile_name)

            # Обновляем состояние строки
            if profile_name in self.profile_rows:
                self.profile_rows[profile_name].update_running_state(False)
                # Устанавливаем причину остановки
                self.profile_rows[profile_name].saved_progress['stop_reason'] = "Остановлен пользователем"

            if success:
                logger.info(f"✅ Профиль {profile_name} успешно остановлен через модуль")
            else:
                logger.warning(f"⚠️ Не удалось остановить профиль {profile_name} через модуль")
        except Exception as e:
            logger.error(f"❌ Ошибка остановки профиля {profile_name}: {e}")

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

        # Удаляем старый если есть
        if profile_name in self.profile_rows:
            self.remove_profile(profile_name)

        profile_row = InviterProfileRow(profile_data)

        # Подключаем сигналы
        profile_row.profile_started.connect(self._on_profile_started)
        profile_row.profile_stopped.connect(self._on_profile_stopped)
        profile_row.profile_deleted.connect(self._on_profile_deleted)

        self.profile_rows[profile_name] = profile_row

        # Вставляем перед растяжкой
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
        """Запускает все профили"""
        for profile_row in self.profile_rows.values():
            if not profile_row.is_running:
                profile_row._toggle_profile()

    def stop_all_profiles(self):
        """Останавливает все профили"""
        for profile_row in self.profile_rows.values():
            if profile_row.is_running:
                profile_row._toggle_profile()

    def refresh_data(self):
        """Обновляет данные профилей"""
        logger.info("🔄 Обновляем данные профилей инвайтера...")

        try:
            from src.modules.impl.inviter import get_all_profiles_for_gui

            # Получаем актуальные данные профилей
            profiles_data = get_all_profiles_for_gui()

            # Очищаем текущие профили
            self.clear_profiles()

            # Загружаем новые профили
            for profile_data in profiles_data:
                self.add_profile(profile_data)

            logger.info(f"✅ Данные профилей обновлены: {len(profiles_data)} профилей")

        except Exception as e:
            logger.error(f"❌ Ошибка обновления данных профилей: {e}")

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