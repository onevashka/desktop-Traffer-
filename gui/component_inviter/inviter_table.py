# gui/component_inviter/inviter_table.py
"""
Компонент таблицы профилей инвайтера с двухэтажными строками
"""

from gui.dialogs.inviter_dialogs import (
    show_users_base_dialog,
    show_chats_base_dialog,
    show_extended_settings_dialog
)

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QFrame,
    QLabel, QPushButton, QComboBox, QSpinBox, QCheckBox,
    QProgressBar, QSizePolicy, QGraphicsOpacityEffect
)
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, Signal
from PySide6.QtGui import QFont, QColor
from loguru import logger


class InviterProfileRow(QWidget):
    """Двухэтажная строка профиля инвайтера"""

    # Сигналы
    profile_started = Signal(str)  # profile_name
    profile_stopped = Signal(str)  # profile_name
    profile_deleted = Signal(str)  # profile_name
    settings_changed = Signal(str, dict)  # profile_name, settings

    def __init__(self, profile_data):
        super().__init__()
        self.profile_data = profile_data
        self.profile_name = profile_data.get('name', 'Профиль')
        self.is_running = profile_data.get('is_running', False)

        self.users_list = profile_data.get('users_list', [])
        self.chats_list = profile_data.get('chats_list', [])
        self.extended_settings = profile_data.get('extended_settings', {})

        self.setObjectName("InviterProfileRow")
        self.setFixedHeight(140)  # Двухэтажная высота

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

        self.users_btn.clicked.connect(self._on_users_settings)
        self.chats_btn.clicked.connect(self._on_chats_settings)
        self.settings_btn.clicked.connect(self._on_extended_settings)

    def _create_first_floor(self, main_layout):
        """Создает первый этаж с основными настройками"""
        first_floor = QWidget()
        layout = QHBoxLayout(first_floor)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # 1. Индикатор статуса и кнопка запуска
        status_widget = self._create_status_widget()
        layout.addWidget(status_widget)

        # 2. Название профиля
        name_widget = self._create_name_widget()
        layout.addWidget(name_widget)

        # 3. Тип инвайта
        invite_type = self._create_invite_type_widget()
        layout.addWidget(invite_type)

        # 4. База пользователей
        users_base = self._create_users_base_widget()
        layout.addWidget(users_base)

        # 5. База чатов
        chats_base = self._create_chats_base_widget()
        layout.addWidget(chats_base)

        # 6. Настройки потоков
        threads_settings = self._create_threads_settings()
        layout.addWidget(threads_settings)

        # 7. Лимиты
        limits_settings = self._create_limits_settings()
        layout.addWidget(limits_settings)

        # 8. Безопасность
        security_settings = self._create_security_settings()
        layout.addWidget(security_settings)

        # 9. Кнопки управления
        control_buttons = self._create_control_buttons()
        layout.addWidget(control_buttons)

        main_layout.addWidget(first_floor)

    def _create_second_floor(self, main_layout):
        """Создает второй этаж со счетчиками и прогрессом"""
        second_floor = QWidget()
        layout = QHBoxLayout(second_floor)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)

        # Прогресс бар общий
        progress_widget = self._create_progress_widget()
        layout.addWidget(progress_widget)

        # Счетчики
        counters_widget = self._create_counters_widget()
        layout.addWidget(counters_widget)

        # Статус последнего действия
        status_widget = self._create_last_status_widget()
        layout.addWidget(status_widget)

        main_layout.addWidget(second_floor)

    def _create_status_widget(self):
        """Индикатор статуса и кнопка запуска"""
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

        # Кнопка запуска/остановки
        self.start_stop_btn = QPushButton("▶️" if not self.is_running else "⏸️")
        self.start_stop_btn.setFixedSize(30, 30)
        self.start_stop_btn.clicked.connect(self._toggle_profile)

        layout.addWidget(self.status_indicator)
        layout.addWidget(self.start_stop_btn)

        return widget

    def _create_name_widget(self):
        """Название профиля"""
        widget = QWidget()
        widget.setFixedWidth(120)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        name_label = QLabel("Профиль:")
        name_label.setStyleSheet("font-size: 11px; color: rgba(255,255,255,0.6);")

        self.name_value = QLabel(self.profile_name)
        self.name_value.setStyleSheet("font-size: 13px; font-weight: 600; color: #FFFFFF;")

        layout.addWidget(name_label)
        layout.addWidget(self.name_value)

        return widget

    def _create_invite_type_widget(self):
        """Тип инвайта"""
        widget = QWidget()
        widget.setFixedWidth(100)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        type_label = QLabel("Тип:")
        type_label.setStyleSheet("font-size: 11px; color: rgba(255,255,255,0.6);")

        self.invite_type_combo = QComboBox()
        self.invite_type_combo.addItems(["Классический", "Через админку"])
        self.invite_type_combo.setFixedHeight(25)

        layout.addWidget(type_label)
        layout.addWidget(self.invite_type_combo)

        return widget

    def _create_users_base_widget(self):
        """База пользователей"""
        widget = QWidget()
        widget.setFixedWidth(90)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        users_label = QLabel("База юзеров:")
        users_label.setStyleSheet("font-size: 11px; color: rgba(255,255,255,0.6);")

        # ← ОБНОВИТЕ ЭТИ СТРОКИ
        users_count = len(self.users_list)
        button_text = f"📝 {users_count} юзеров" if users_count > 0 else "📝 Настроить"

        self.users_btn = QPushButton(button_text)
        self.users_btn.setFixedHeight(25)
        self.users_btn.setStyleSheet("""
            QPushButton {
                background: rgba(59, 130, 246, 0.2);
                border: 1px solid rgba(59, 130, 246, 0.5);
                border-radius: 4px;
                color: #FFFFFF;
                font-size: 10px;
            }
            QPushButton:hover {
                background: rgba(59, 130, 246, 0.3);
            }
        """)

        layout.addWidget(users_label)
        layout.addWidget(self.users_btn)

        return widget

    def _create_chats_base_widget(self):
        """База чатов"""
        widget = QWidget()
        widget.setFixedWidth(90)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        chats_label = QLabel("База чатов:")
        chats_label.setStyleSheet("font-size: 11px; color: rgba(255,255,255,0.6);")

        # ← ОБНОВИТЕ ЭТИ СТРОКИ
        chats_count = len(self.chats_list)
        button_text = f"📝 {chats_count} чатов" if chats_count > 0 else "📝 Настроить"

        self.chats_btn = QPushButton(button_text)
        self.chats_btn.setFixedHeight(25)
        self.chats_btn.setStyleSheet("""
            QPushButton {
                background: rgba(16, 185, 129, 0.2);
                border: 1px solid rgba(16, 185, 129, 0.5);
                border-radius: 4px;
                color: #FFFFFF;
                font-size: 10px;
            }
            QPushButton:hover {
                background: rgba(16, 185, 129, 0.3);
            }
        """)

        layout.addWidget(chats_label)
        layout.addWidget(self.chats_btn)

        return widget

    def _create_threads_settings(self):
        """Настройки потоков"""
        widget = QWidget()
        widget.setFixedWidth(100)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        threads_label = QLabel("Потоков на чат:")
        threads_label.setStyleSheet("font-size: 11px; color: rgba(255,255,255,0.6);")

        self.threads_spin = QSpinBox()
        self.threads_spin.setRange(1, 10)
        self.threads_spin.setValue(2)
        self.threads_spin.setFixedHeight(25)

        layout.addWidget(threads_label)
        layout.addWidget(self.threads_spin)

        return widget

    def _create_limits_settings(self):
        """Настройки лимитов"""
        widget = QWidget()
        widget.setFixedWidth(120)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        # Лимит на чат
        chat_limit_layout.addWidget(chat_limit_label)
        chat_limit_layout.addWidget(self.chat_limit_spin)

        # Лимит на аккаунт
        acc_limit_layout = QHBoxLayout()
        acc_limit_layout.setSpacing(5)

        acc_limit_label = QLabel("Акк:")
        acc_limit_label.setStyleSheet("font-size: 10px; color: rgba(255,255,255,0.6);")

        self.acc_limit_spin = QSpinBox()
        self.acc_limit_spin.setRange(1, 1000)
        self.acc_limit_spin.setValue(100)
        self.acc_limit_spin.setFixedSize(50, 20)

        acc_limit_layout.addWidget(acc_limit_label)
        acc_limit_layout.addWidget(self.acc_limit_spin)

        layout.addLayout(chat_limit_layout)
        layout.addLayout(acc_limit_layout)

        return widget

    def _create_security_settings(self):
        """Настройки безопасности"""
        widget = QWidget()
        widget.setFixedWidth(140)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        # Спамблок лимит
        spam_layout = QHBoxLayout()
        spam_layout.setSpacing(5)

        spam_label = QLabel("Спам:")
        spam_label.setStyleSheet("font-size: 10px; color: rgba(255,255,255,0.6);")

        self.spam_limit_spin = QSpinBox()
        self.spam_limit_spin.setRange(1, 50)
        self.spam_limit_spin.setValue(3)
        self.spam_limit_spin.setFixedSize(40, 20)

        spam_layout.addWidget(spam_label)
        spam_layout.addWidget(self.spam_limit_spin)

        # Списания лимит
        writeoff_layout = QHBoxLayout()
        writeoff_layout.setSpacing(5)

        writeoff_label = QLabel("Списан:")
        writeoff_label.setStyleSheet("font-size: 10px; color: rgba(255,255,255,0.6);")

        self.writeoff_limit_spin = QSpinBox()
        self.writeoff_limit_spin.setRange(1, 20)
        self.writeoff_limit_spin.setValue(2)
        self.writeoff_limit_spin.setFixedSize(40, 20)

        writeoff_layout.addWidget(writeoff_label)
        writeoff_layout.addWidget(self.writeoff_limit_spin)

        layout.addLayout(spam_layout)
        layout.addLayout(writeoff_layout)

        return widget

    def _create_control_buttons(self):
        """Кнопки управления профилем"""
        widget = QWidget()
        widget.setFixedWidth(80)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Кнопка настроек
        self.settings_btn = QPushButton("⚙️")
        self.settings_btn.setFixedSize(30, 25)
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
        self.delete_btn.setFixedSize(30, 25)
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
        self.delete_btn.clicked.connect(self._delete_profile)

        layout.addWidget(self.settings_btn)
        layout.addWidget(self.delete_btn)

        return widget

    def _create_progress_widget(self):
        """Общий прогресс бар"""
        widget = QWidget()
        widget.setFixedWidth(200)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        progress_label = QLabel("Общий прогресс:")
        progress_label.setStyleSheet("font-size: 11px; color: rgba(255,255,255,0.6);")

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(20)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
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

    def _create_counters_widget(self):
        """Виджет со счетчиками"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)

        # Успешные инвайты
        success_widget = self._create_counter("Успешно:", "0", "#10B981")
        layout.addWidget(success_widget)

        # Ошибки
        errors_widget = self._create_counter("Ошибки:", "0", "#EF4444")
        layout.addWidget(errors_widget)

        # Всего обработано
        total_widget = self._create_counter("Всего:", "0", "#3B82F6")
        layout.addWidget(total_widget)

        return widget

    def _create_counter(self, label_text, value, color):
        """Создает отдельный счетчик"""
        widget = QWidget()
        widget.setFixedWidth(80)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        label = QLabel(label_text)
        label.setStyleSheet("font-size: 10px; color: rgba(255,255,255,0.6);")
        label.setAlignment(Qt.AlignCenter)

        value_label = QLabel(value)
        value_label.setStyleSheet(f"""
            font-size: 14px; 
            font-weight: 600; 
            color: {color};
        """)
        value_label.setAlignment(Qt.AlignCenter)

        layout.addWidget(label)
        layout.addWidget(value_label)

        return widget

    def _create_last_status_widget(self):
        """Статус последнего действия"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        status_label = QLabel("Последнее действие:")
        status_label.setStyleSheet("font-size: 11px; color: rgba(255,255,255,0.6);")

        self.last_action_label = QLabel("Ожидание...")
        self.last_action_label.setStyleSheet("""
            font-size: 12px; 
            color: rgba(255,255,255,0.8);
            background: rgba(255, 255, 255, 0.05);
            border-radius: 4px;
            padding: 4px 8px;
        """)

        layout.addWidget(status_label)
        layout.addWidget(self.last_action_label)

        return widget

    def _apply_styles(self):
        """Применяет стили к строке профиля"""
        self.setStyleSheet("""
            QWidget#InviterProfileRow {
                background: rgba(255, 255, 255, 0.03);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 12px;
                margin: 2px 0;
            }
            QWidget#InviterProfileRow:hover {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(59, 130, 246, 0.3);
            }
            QSpinBox {
                background: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 4px;
                color: #FFFFFF;
                font-size: 11px;
                padding: 2px;
            }
            QSpinBox:focus {
                border-color: #3B82F6;
            }
            QComboBox {
                background: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 4px;
                color: #FFFFFF;
                font-size: 11px;
                padding: 2px 4px;
            }
            QComboBox:focus {
                border-color: #3B82F6;
            }
            QComboBox QAbstractItemView {
                background: rgba(30, 30, 30, 0.95);
                border: 1px solid rgba(255, 255, 255, 0.1);
                selection-background-color: rgba(59, 130, 246, 0.3);
                color: #FFFFFF;
            }
        """)

    def _toggle_profile(self):
        """Переключает состояние профиля"""
        self.is_running = not self.is_running

        # Обновляем индикатор
        self.status_indicator.setStyleSheet(f"""
            QLabel {{
                font-size: 16px;
                color: {'#10B981' if self.is_running else '#6B7280'};
                font-weight: bold;
            }}
        """)

        # Обновляем кнопку
        self.start_stop_btn.setText("⏸️" if self.is_running else "▶️")

        # Эмитим сигнал
        if self.is_running:
            self.profile_started.emit(self.profile_name)
            self.last_action_label.setText("Запущен...")
        else:
            self.profile_stopped.emit(self.profile_name)
            self.last_action_label.setText("Остановлен")

    def _delete_profile(self):
        """Удаляет профиль"""
        self.profile_deleted.emit(self.profile_name)

    def update_progress(self, value):
        """Обновляет прогресс бар"""
        self.progress_bar.setValue(value)

    def update_counters(self, success, errors, total):
        """Обновляет счетчики"""
        # Найдем виджеты счетчиков и обновим их
        pass  # TODO: Реализовать обновление счетчиков

    def update_last_action(self, action_text):
        """Обновляет текст последнего действия"""
        self.last_action_label.setText(action_text)


class InviterTableWidget(QWidget):
    """Основная таблица с профилями инвайтера"""

    def __init__(self):
        super().__init__()
        self.setObjectName("InviterTableWidget")

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

    def _load_test_profiles(self):
        """Загружает тестовые профили"""
        test_profiles = [
            {
                'name': 'Профиль #1',
                'is_running': False,
                'invite_type': 'Классический',
                'threads': 2,
                'chat_limit': 50,
                'acc_limit': 100
            },
            {
                'name': 'Профиль #2',
                'is_running': True,
                'invite_type': 'Через админку',
                'threads': 3,
                'chat_limit': 75,
                'acc_limit': 150
            },
            {
                'name': 'Профиль #3',
                'is_running': False,
                'invite_type': 'Классический',
                'threads': 1,
                'chat_limit': 30,
                'acc_limit': 80
            }
        ]

        self.profile_rows = []
        for profile_data in test_profiles:
            profile_row = InviterProfileRow(profile_data)

            # Подключаем сигналы
            profile_row.profile_started.connect(self._on_profile_started)
            profile_row.profile_stopped.connect(self._on_profile_stopped)
            profile_row.profile_deleted.connect(self._on_profile_deleted)

            self.profile_rows.append(profile_row)
            self.profiles_layout.addWidget(profile_row)

        # Добавляем растяжку в конце
        self.profiles_layout.addStretch()

    def _on_profile_started(self, profile_name):
        """Обработка запуска профиля"""
        logger.info(f"🚀 Профиль запущен: {profile_name}")
        # TODO: Запустить логику инвайтера для профиля

    def _on_profile_stopped(self, profile_name):
        """Обработка остановки профиля"""
        logger.info(f"⏸️ Профиль остановлен: {profile_name}")
        # TODO: Остановить логику инвайтера для профиля

    def _on_profile_deleted(self, profile_name):
        """Обработка удаления профиля"""
        logger.info(f"🗑️ Удаление профиля: {profile_name}")
        # TODO: Показать диалог подтверждения и удалить профиль

    def add_profile(self, profile_data):
        """Добавляет новый профиль"""
        profile_row = InviterProfileRow(profile_data)

        # Подключаем сигналы
        profile_row.profile_started.connect(self._on_profile_started)
        profile_row.profile_stopped.connect(self._on_profile_stopped)
        profile_row.profile_deleted.connect(self._on_profile_deleted)

        self.profile_rows.append(profile_row)

        # Вставляем перед растяжкой
        self.profiles_layout.insertWidget(len(self.profile_rows) - 1, profile_row)

    def remove_profile(self, profile_name):
        """Удаляет профиль"""
        for i, profile_row in enumerate(self.profile_rows):
            if profile_row.profile_name == profile_name:
                profile_row.deleteLater()
                self.profile_rows.pop(i)
                break

    def start_all_profiles(self):
        """Запускает все профили"""
        for profile_row in self.profile_rows:
            if not profile_row.is_running:
                profile_row._toggle_profile()

    def stop_all_profiles(self):
        """Останавливает все профили"""
        for profile_row in self.profile_rows:
            if profile_row.is_running:
                profile_row._toggle_profile()

    def refresh_data(self):
        """Обновляет данные профилей"""
        logger.info("🔄 Обновляем данные профилей инвайтера...")
        # TODO: Реализовать обновление данных

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
            _layout = QHBoxLayout()
        chat_limit_layout.setSpacing(5)

        chat_limit_label = QLabel("Чат:")
        chat_limit_label.setStyleSheet("font-size: 10px; color: rgba(255,255,255,0.6);")

        self.chat_limit_spin = QSpinBox()
        self.chat_limit_spin.setRange(1, 1000)
        self.chat_limit_spin.setValue(50)
        self.chat_limit_spin.setFixedSize(50, 20)

        chat_limit

    def _on_users_settings(self):
        """Настройка базы пользователей"""
        try:
            current_users = getattr(self, 'users_list', [])
            users = show_users_base_dialog(self, current_users)
            if users != current_users:
                self.users_list = users
                users_count = len(users)
                button_text = f"📝 {users_count} юзеров" if users_count > 0 else "📝 Настроить"
                self.users_btn.setText(button_text)
                logger.info(f"🔄 Обновлена база пользователей для {self.profile_name}: {len(users)} пользователей")
        except Exception as e:
            logger.error(f"❌ Ошибка настройки пользователей: {e}")

    def _on_chats_settings(self):
        """Настройка базы чатов"""
        try:
            current_chats = getattr(self, 'chats_list', [])
            chats = show_chats_base_dialog(self, current_chats)
            if chats != current_chats:
                self.chats_list = chats
                chats_count = len(chats)
                button_text = f"📝 {chats_count} чатов" if chats_count > 0 else "📝 Настроить"
                self.chats_btn.setText(button_text)
                logger.info(f"🔄 Обновлена база чатов для {self.profile_name}: {len(chats)} чатов")
        except Exception as e:
            logger.error(f"❌ Ошибка настройки чатов: {e}")

    def _on_extended_settings(self):
        """Расширенные настройки профиля"""
        try:
            current_settings = getattr(self, 'extended_settings', {})
            settings = show_extended_settings_dialog(self, current_settings)
            if settings != current_settings:
                self.extended_settings = settings
                logger.info(f"⚙️ Обновлены расширенные настройки для {self.profile_name}")
        except Exception as e:
            logger.error(f"❌ Ошибка настройки профиля: {e}")