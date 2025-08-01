# gui/component_inviter/inviter_table.py - ИСПРАВЛЕННАЯ ВЕРСИЯ СОХРАНЕНИЯ
"""
Компонент таблицы профилей инвайтера с двухэтажными строками
ИСПРАВЛЕНО СОХРАНЕНИЕ В ФАЙЛЫ ЧЕРЕЗ МОДУЛЬ
"""

from gui.dialogs.inviter_dialogs import (
    show_users_base_dialog,
    show_chats_base_dialog,
    show_extended_settings_dialog
)

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QFrame,
    QLabel, QPushButton, QComboBox, QSpinBox, QCheckBox,
    QProgressBar, QSizePolicy, QGraphicsOpacityEffect, QLineEdit
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
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.profile_data = profile_data
        self.profile_name = profile_data.get('name', 'Профиль')
        self.is_running = profile_data.get('is_running', False)

        self.users_list = profile_data.get('users_list', [])
        self.chats_list = profile_data.get('chats_list', [])
        self.extended_settings = profile_data.get('extended_settings', {})

        self.setObjectName("InviterProfileRow")
        self.setFixedHeight(140)  # Двухэтажная высота

        # ИСПРАВЛЕНО: Инициализируем кнопки как None
        self.users_btn = None
        self.chats_btn = None
        self.settings_btn = None
        self.delete_btn = None
        self.start_stop_btn = None
        self.name_edit = None

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

        # ИСПРАВЛЕНО: Подключаем обработчики ПОСЛЕ создания всех кнопок
        self._connect_signals()

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

        except Exception as e:
            logger.error(f"❌ Ошибка подключения сигналов для {self.profile_name}: {e}")

    def _create_first_floor(self, main_layout):
        """Создает первый этаж с основными настройками"""
        first_floor = QWidget()
        layout = QHBoxLayout(first_floor)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # 1. Индикатор статуса и кнопка запуска
        layout.addWidget(self._create_status_widget())

        layout.addWidget(self._create_start_button_widget())

        # 2. Название профиля
        layout.addWidget(self._create_name_widget())

        # 3. Тип инвайта
        layout.addWidget(self._create_invite_type_widget())

        # 4. База пользователей
        layout.addWidget(self._create_users_base_widget())

        # 5. База чатов
        layout.addWidget(self._create_chats_base_widget())

        # 9. Кнопки управления
        layout.addWidget(self._create_control_buttons())

        main_layout.addWidget(first_floor)

    def _create_second_floor(self, main_layout):
        """Только один растянутый прогресс-бар"""
        progress_widget = self._create_progress_widget()
        progress_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        main_layout.addWidget(progress_widget)

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

        layout.addWidget(self.status_indicator)

        return widget

    def _create_start_button_widget(self):
        """Кнопка Запустить/Стоп цветная."""
        widget = QWidget()
        widget.setFixedWidth(120)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignCenter)

        # ИСПРАВЛЕНО: создаём кнопку и сохраняем ссылку
        self.start_stop_btn = QPushButton()
        self._update_start_button()  # задаст текст и цвет
        self.start_stop_btn.setFixedSize(100, 40)
        # НЕ подключаем сигнал здесь - это делается в _connect_signals()

        layout.addWidget(self.start_stop_btn)
        return widget

    def _update_start_button(self):
        """Обновляет текст и цвет кнопки в зависимости от состояния."""
        if not self.start_stop_btn:
            return

        if self.is_running:
            self.start_stop_btn.setText("Стоп")
            self.start_stop_btn.setStyleSheet("background: #EF4444; color: white; border-radius: 4px;")
        else:
            self.start_stop_btn.setText("Запустить")
            self.start_stop_btn.setStyleSheet("background: #10B981; color: white; border-radius: 4px;")

    def _create_name_widget(self):
        """Название профиля — теперь редактируемое поле и побольше."""
        widget = QWidget()
        # расширили ширину контейнера
        widget.setFixedWidth(200)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        name_label = QLabel("Профиль:")
        name_label.setStyleSheet("font-size: 12px; color: rgba(255,255,255,0.6);")

        # ИСПРАВЛЕНО: теперь QLineEdit вместо QLabel и сохраняем ссылку
        self.name_edit = QLineEdit(self.profile_name)
        self.name_edit.setFixedWidth(180)  # увеличенная ширина
        self.name_edit.setFixedHeight(28)  # чуть повыше
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
        # НЕ подключаем сигнал здесь - это делается в _connect_signals()

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
            # эмитим сигнал, чтобы внешний код узнал об изменении
            self.settings_changed.emit(self.profile_name, {'name': new_name})

    def _create_invite_type_widget(self):
        """Тип инвайта — увеличили размер выпадашки."""
        widget = QWidget()
        widget.setFixedWidth(200)  # расширили контейнер
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        type_label = QLabel("Тип инвайта:")
        type_label.setStyleSheet("font-size: 12px; color: rgba(255,255,255,0.6);")

        self.invite_type_combo = QComboBox()
        self.invite_type_combo.addItems(["Классический", "Через админку"])
        self.invite_type_combo.setFixedWidth(180)  # увеличенная ширина
        self.invite_type_combo.setFixedHeight(28)  # чуть повыше
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

        layout.addWidget(type_label)
        layout.addWidget(self.invite_type_combo)
        return widget

    def _create_users_base_widget(self):
        """База пользователей — кнопка с большим шрифтом текста"""
        widget = QWidget()
        widget.setFixedWidth(90)  # обратно к вашему фиксированному весу
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        users_count = len(self.users_list)
        button_text = f"Юзеров: {users_count}" if users_count else "Юзеров: 0"

        # ИСПРАВЛЕНО: сохраняем ссылку на кнопку
        self.users_btn = QPushButton(button_text)
        self.users_btn.setFixedHeight(25)  # ваш исходный фиксированный рост
        self.users_btn.setStyleSheet("""
            QPushButton {
                background: rgba(59, 130, 246, 0.2);
                border: 1px solid rgba(59, 130, 246, 0.5);
                border-radius: 4px;
                color: #FFFFFF;
                font-size: 14px;         /* увеличили текст */
                font-weight: 600;        /* можно чуть жирнее */
            }
            QPushButton:hover {
                background: rgba(59, 130, 246, 0.3);
            }
        """)
        # НЕ подключаем сигнал здесь - это делается в _connect_signals()

        layout.addWidget(self.users_btn)
        return widget

    def _create_chats_base_widget(self):
        """База чатов — кнопка с большим шрифтом текста"""
        widget = QWidget()
        widget.setFixedWidth(90)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        chats_count = len(self.chats_list)
        button_text = f"Чатов: {chats_count}" if chats_count else "Чатов: 0"

        # ИСПРАВЛЕНО: сохраняем ссылку на кнопку
        self.chats_btn = QPushButton(button_text)
        self.chats_btn.setFixedHeight(25)
        self.chats_btn.setStyleSheet("""
            QPushButton {
                background: rgba(16, 185, 129, 0.2);
                border: 1px solid rgba(16, 185, 129, 0.5);
                border-radius: 4px;
                color: #FFFFFF;
                color: #FFFFFF;
                font-size: 14px;         /* увеличили текст */
                font-weight: 600;
            }
            QPushButton:hover {
                background: rgba(16, 185, 129, 0.3);
            }
        """)
        # НЕ подключаем сигнал здесь - это делается в _connect_signals()

        layout.addWidget(self.chats_btn)
        return widget

    def _create_control_buttons(self):
        """Кнопки управления профилем"""
        widget = QWidget()
        widget.setFixedWidth(80)
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # ИСПРАВЛЕНО: сохраняем ссылки на кнопки
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
        # НЕ подключаем сигнал здесь - это делается в _connect_signals()

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
        # НЕ подключаем сигнал здесь - это делается в _connect_signals()

        layout.addWidget(self.settings_btn)
        layout.addWidget(self.delete_btn)

        return widget

    def _create_progress_widget(self):
        """Общий прогресс бар"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        progress_label = QLabel("Общий прогресс:")
        progress_label.setStyleSheet("font-size: 11px; color: rgba(255,255,255,0.6);")

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(24)
        # максимум мы будем задавать динамически
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(0)
        # Показывать текст "сделано из всего"
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%v из %m")

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

    def _apply_styles(self):
        """Применяет стили к строке профиля"""
        # Обновлённая стилизация для чёткого выделения профиля
        self.setStyleSheet("""
            QWidget#InviterProfileRow {
                background: #1F2937; /* темно-серый фон */
                border: 1px solid #4B5563; /* контрастная рамка */
                border-radius: 8px;
                padding: 8px;
                margin: 6px 0;
            }
            QWidget#InviterProfileRow:hover {
                background: #374151; /* подсветка */
                border: 1px solid #2563EB; /* синий акцент */
            }
            QSpinBox {
                background: #111827;
                border: 1px solid #374151;
                border-radius: 4px;
                color: #FFFFFF;
                font-size: 11px;
                padding: 2px;
            }
            QSpinBox:focus {
                border-color: #2563EB;
            }
            QComboBox {
                background: #111827;
                border: 1px solid #374151;
                border-radius: 4px;
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
        self._update_start_button()

        # Эмитим сигнал
        if self.is_running:
            self.profile_started.emit(self.profile_name)
            if hasattr(self, 'last_action_label'):
                self.last_action_label.setText("Запущен...")
        else:
            self.profile_stopped.emit(self.profile_name)
            if hasattr(self, 'last_action_label'):
                self.last_action_label.setText("Остановлен")

    def _delete_profile(self):
        """Удаляет профиль"""
        self.profile_deleted.emit(self.profile_name)

    def _on_users_settings(self):
        """ИСПРАВЛЕНО: Настройка базы пользователей С СОХРАНЕНИЕМ ЧЕРЕЗ МОДУЛЬ"""
        try:
            logger.info(f"🔧 Открываем настройки пользователей для профиля: {self.profile_name}")

            current_users = getattr(self, 'users_list', [])
            logger.info(f"📝 Текущих пользователей в памяти: {len(current_users)}")
            if current_users:
                logger.info(f"📝 Первые 3 пользователя: {current_users[:3]}")

            # Показываем диалог
            users = show_users_base_dialog(self, current_users)

            # ИСПРАВЛЕНО: Проверяем что вернулся не None и отличается от текущего
            if users is not None:
                logger.info(f"📥 Получено пользователей из диалога: {len(users)}")
                if users:
                    logger.info(f"📥 Первые 3 полученных: {users[:3]}")

                # КЛЮЧЕВОЕ ИСПРАВЛЕНИЕ: Всегда сохраняем через модуль
                logger.info(f"💾 Сохраняем пользователей через модуль для {self.profile_name}")

                # Импортируем модуль
                from src.modules.impl.inviter import update_profile_users

                # Сохраняем в модуле (который сохранит в файл)
                success = update_profile_users(self.profile_name, users)

                if success:
                    # ИСПРАВЛЕНО: Обновляем локальные данные ТОЛЬКО после успешного сохранения
                    self.users_list = users
                    users_count = len(users)
                    button_text = f"Юзеров: {users_count}"
                    if self.users_btn:
                        self.users_btn.setText(button_text)

                    logger.info(f"✅ База пользователей обновлена для {self.profile_name}: {users_count} пользователей")

                    # Показываем уведомление об успехе
                    try:
                        from gui.notifications import show_success
                        show_success(
                            "База пользователей",
                            f"✅ Сохранено {users_count} пользователей\nВ файл: База юзеров.txt"
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
            try:
                from gui.notifications import show_error
                show_error(
                    "Критическая ошибка",
                    f"❌ Ошибка настройки пользователей: {e}"
                )
            except:
                pass

    def _on_chats_settings(self):
        """ИСПРАВЛЕНО: Настройка базы чатов С СОХРАНЕНИЕМ ЧЕРЕЗ МОДУЛЬ"""
        try:
            logger.info(f"🔧 Открываем настройки чатов для профиля: {self.profile_name}")

            current_chats = getattr(self, 'chats_list', [])
            logger.info(f"💬 Текущих чатов в памяти: {len(current_chats)}")
            if current_chats:
                logger.info(f"💬 Первые 3 чата: {current_chats[:3]}")

            # Показываем диалог
            chats = show_chats_base_dialog(self, current_chats)

            # ИСПРАВЛЕНО: Проверяем что вернулся не None и отличается от текущего
            if chats is not None:
                logger.info(f"📥 Получено чатов из диалога: {len(chats)}")
                if chats:
                    logger.info(f"📥 Первые 3 полученных: {chats[:3]}")

                # КЛЮЧЕВОЕ ИСПРАВЛЕНИЕ: Всегда сохраняем через модуль
                logger.info(f"💾 Сохраняем чаты через модуль для {self.profile_name}")

                # Импортируем модуль
                from src.modules.impl.inviter import update_profile_chats

                # Сохраняем в модуле (который сохранит в файл)
                success = update_profile_chats(self.profile_name, chats)

                if success:
                    # ИСПРАВЛЕНО: Обновляем локальные данные ТОЛЬКО после успешного сохранения
                    self.chats_list = chats
                    chats_count = len(chats)
                    button_text = f"Чатов: {chats_count}"
                    if self.chats_btn:
                        self.chats_btn.setText(button_text)

                    logger.info(f"✅ База чатов обновлена для {self.profile_name}: {chats_count} чатов")

                    # Показываем уведомление об успехе
                    try:
                        from gui.notifications import show_success
                        show_success(
                            "База чатов",
                            f"✅ Сохранено {chats_count} чатов\nВ файл: База чатов.txt"
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
            try:
                from gui.notifications import show_error
                show_error(
                    "Критическая ошибка",
                    f"❌ Ошибка настройки чатов: {e}"
                )
            except:
                pass

    def _on_extended_settings(self):
        """Расширенные настройки профиля"""
        try:
            # Получаем актуальный профиль из модуля для гарантии свежих данных
            from src.modules.impl.inviter.inviter_manager import _inviter_module_manager

            if _inviter_module_manager:
                # Получаем свежие данные профиля
                fresh_profile = _inviter_module_manager.profile_manager.get_profile(self.profile_name)
                if fresh_profile:
                    current_config = fresh_profile.get('config', {})
                else:
                    current_config = self.profile_data.get('config', {})
            else:
                current_config = self.profile_data.get('config', {})

            logger.debug(f"📝 Загружаем настройки для {self.profile_name}: {current_config}")

            # Показываем диалог с текущими настройками из конфига
            new_settings = show_extended_settings_dialog(self, current_config)

            # Проверяем что вернулся не None (пользователь нажал Сохранить)
            if new_settings is not None:
                # Сохраняем через модуль
                self._save_extended_settings_to_module(new_settings)

                logger.info(f"⚙️ Обновлены расширенные настройки для {self.profile_name}")

        except Exception as e:
            logger.error(f"❌ Ошибка настройки профиля: {e}")

        except Exception as e:
            logger.error(f"❌ Ошибка настройки профиля: {e}")

    def _save_extended_settings_to_module(self, settings: dict):
        """Сохраняет расширенные настройки через модуль"""
        try:
            from src.modules.impl.inviter import update_profile_config

            # Отправляем в модуль для сохранения в JSON
            success = update_profile_config(self.profile_name, settings)

            if success:
                # ВАЖНО: Обновляем локальные данные config
                if 'config' not in self.profile_data:
                    self.profile_data['config'] = {}

                # Обновляем каждое поле в конфиге
                self.profile_data['config'].update(settings)

                # Обновляем и extended_settings для обратной совместимости
                self.extended_settings = settings

                logger.info(f"✅ Настройки сохранены в JSON для {self.profile_name}")
                logger.debug(f"📝 Обновленный конфиг: {self.profile_data['config']}")

                # Показываем уведомление об успехе
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
        """Обновляем X из Y."""
        if self.progress_bar:
            # обновляем максимум
            self.progress_bar.setRange(0, total)
            # и текущее значение
            self.progress_bar.setValue(done)

    def update_counters(self, success, errors, total):
        """Обновляет счетчики"""
        # Найдем виджеты счетчиков и обновим их
        pass  # TODO: Реализовать обновление счетчиков

    def update_last_action(self, action_text):
        """Обновляет текст последнего действия"""
        if hasattr(self, 'last_action_label'):
            self.last_action_label.setText(action_text)


class InviterTableWidget(QWidget):
    """Основная таблица с профилями инвайтера"""

    def __init__(self):
        super().__init__()
        self.setObjectName("InviterTableWidget")

        # Список строк профилей для отслеживания
        self.profile_rows = []

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

            # ИСПРАВЛЕНО: Подключаем сигналы после создания строки
            row.profile_started.connect(self._on_profile_started)
            row.profile_stopped.connect(self._on_profile_stopped)
            row.profile_deleted.connect(self._on_profile_deleted)

            # Добавляем в список для отслеживания
            self.profile_rows.append(row)
            self.profiles_layout.addWidget(row)

            # Добавляем разделитель сразу после строки
            if i < len(test_profiles) - 1:
                sep = QFrame()
                sep.setFrameShape(QFrame.HLine)
                sep.setFrameShadow(QFrame.Sunken)
                # стиль линии — светло-серая
                sep.setStyleSheet("color: rgba(255,255,255,0.1);")
                sep.setFixedHeight(1)
                self.profiles_layout.addWidget(sep)

        self.profiles_layout.addStretch()

    def _on_profile_started(self, profile_name):
        """Обработка запуска профиля"""
        logger.info(f"🚀 Профиль запущен: {profile_name}")
        # TODO: Запустить логику инвайтера для профиля через модуль
        try:
            from src.modules.impl.inviter import start_profile
            success = start_profile(profile_name)
            if success:
                logger.info(f"✅ Профиль {profile_name} успешно запущен через модуль")
            else:
                logger.warning(f"⚠️ Не удалось запустить профиль {profile_name} через модуль")
        except Exception as e:
            logger.error(f"❌ Ошибка запуска профиля {profile_name}: {e}")

    def _on_profile_stopped(self, profile_name):
        """Обработка остановки профиля"""
        logger.info(f"⏸️ Профиль остановлен: {profile_name}")
        # TODO: Остановить логику инвайтера для профиля через модуль
        try:
            from src.modules.impl.inviter import stop_profile
            success = stop_profile(profile_name)
            if success:
                logger.info(f"✅ Профиль {profile_name} успешно остановлен через модуль")
            else:
                logger.warning(f"⚠️ Не удалось остановить профиль {profile_name} через модуль")
        except Exception as e:
            logger.error(f"❌ Ошибка остановки профиля {profile_name}: {e}")

    def _on_profile_deleted(self, profile_name):
        """Обработка удаления профиля"""
        logger.info(f"🗑️ Удаление профиля: {profile_name}")
        # TODO: Показать диалог подтверждения и удалить профиль через модуль
        try:
            from src.modules.impl.inviter import delete_profile
            result = delete_profile(profile_name)
            if result.get('success'):
                logger.info(f"✅ Профиль {profile_name} успешно удален через модуль")
                # Удаляем строку из интерфейса
                self.remove_profile(profile_name)
            else:
                logger.warning(f"⚠️ Не удалось удалить профиль {profile_name}: {result.get('message')}")
        except Exception as e:
            logger.error(f"❌ Ошибка удаления профиля {profile_name}: {e}")

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
        """Удаляет профиль из интерфейса"""
        for i, profile_row in enumerate(self.profile_rows):
            if profile_row.profile_name == profile_name:
                profile_row.deleteLater()
                self.profile_rows.pop(i)
                logger.info(f"🗑️ Строка профиля {profile_name} удалена из интерфейса")
                break

    def clear_profiles(self):
        """Очищает все профили"""
        for profile_row in self.profile_rows:
            profile_row.deleteLater()
        self.profile_rows.clear()
        logger.info("🧹 Все профили очищены из интерфейса")

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
        # TODO: Реализовать обновление данных через модуль
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