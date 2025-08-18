# gui/component_inviter/inviter_table.py - ОПТИМИЗИРОВАННАЯ ВЕРСИЯ С КОМПАКТНОЙ ШАПКОЙ

from gui.dialogs.inviter_dialogs import (
    show_users_base_dialog,
    show_chats_base_dialog,
    show_extended_settings_dialog
)
from gui.dialogs.main_admins_dialog import show_main_admins_dialog
from gui.dialogs.bot_token_dialog import show_bot_token_dialog, load_bot_token_from_profile

from src.modules.impl.inviter.profile_manager import InviterProfileManager

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QFrame,
    QLabel, QPushButton, QComboBox, QSpinBox, QCheckBox,
    QProgressBar, QSizePolicy, QGraphicsOpacityEffect, QLineEdit,
    QGridLayout
)
from PySide6.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve, Signal,
    QParallelAnimationGroup
)
from PySide6.QtGui import QFont, QColor, QPainter, QPen, QBrush
from loguru import logger
from typing import Optional, Dict, List


class ChatStatWidget(QWidget):
    """Компактный виджет для отображения статистики одного чата с четкими счетчиками"""

    def __init__(self, chat_link: str, stats: Dict):
        super().__init__()
        self.chat_link = chat_link
        self.stats = stats

        # Значительно увеличили общую высоту для больших чисел и названий
        self.setFixedHeight(140)  # Увеличили с 110 до 140 для большей области
        self.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(31, 41, 55, 0.95), stop:1 rgba(17, 24, 39, 0.95));
                border-radius: 8px;
                margin: 2px;
            }
            QWidget:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(45, 55, 71, 1), stop:1 rgba(25, 35, 49, 1));
            }
        """)

        self._create_layout()

    def _create_layout(self):
        """Создает компактный layout с двумя секциями"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 4, 8, 4)
        main_layout.setSpacing(4)

        # Верхняя часть: Название чата + прогресс-бар
        top_layout = QHBoxLayout()
        top_layout.setSpacing(8)

        # 1. Левая часть: Название чата + статус (160px)
        left_widget = self._create_chat_name_section()
        left_widget.setFixedWidth(160)
        top_layout.addWidget(left_widget)

        # 2. Правая часть: Прогресс-бар (растягивается)
        progress_widget = self._create_progress_section()
        top_layout.addWidget(progress_widget)

        main_layout.addLayout(top_layout)

        # Нижняя часть: Все счетчики под прогресс-баром (увеличена область)
        counters_widget = self._create_all_counters_section()
        main_layout.addWidget(counters_widget)

    def _create_chat_name_section(self):
        """Создает секцию с названием чата и статусом"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(1)

        # Название чата (обрезаем длинные названия)
        chat_name = self.chat_link.split('/')[-1] if '/' in self.chat_link else self.chat_link
        if len(chat_name) > 20:
            chat_name = chat_name[:17] + "..."

        name_label = QLabel(f"💬 {chat_name}")
        name_label.setStyleSheet("""
            QLabel {
                font-size: 11px;
                font-weight: 700;
                color: #FFFFFF;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(59, 130, 246, 0.25), stop:1 rgba(139, 92, 246, 0.25));
                padding: 2px 6px;
                border-radius: 3px;
                border: 1px solid rgba(59, 130, 246, 0.3);
            }
        """)

        # Статус чата
        status = self.stats.get('status', 'active')
        if status == 'blocked':
            status_text = "🚫 Заблокирован"
            status_color = "#EF4444"
        elif status == 'completed':
            status_text = "✅ Завершен"
            status_color = "#10B981"
        else:
            status_text = "🟢 Активен"
            status_color = "#10B981"

        status_label = QLabel(status_text)
        status_label.setStyleSheet(f"""
            QLabel {{
                font-size: 9px;
                color: {status_color};
                font-weight: 600;
                padding: 1px 4px;
                background: {status_color}15;
                border-radius: 2px;
            }}
        """)

        layout.addWidget(name_label)
        layout.addWidget(status_label)
        layout.addStretch()

        return widget

    def _create_progress_section(self):
        """Создает секцию с прогресс-баром"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(2)

        # Заголовок прогресса
        progress_header = QLabel("Прогресс инвайтинга:")
        progress_header.setStyleSheet("""
            QLabel {
                font-size: 9px;
                color: rgba(255, 255, 255, 0.7);
                font-weight: 600;
            }
        """)

        # Прогресс-бар с подробной информацией
        progress = QProgressBar()
        progress.setFixedHeight(16)

        success = self.stats.get('success', 0)
        goal = self.stats.get('goal', 100)
        total_attempts = self.stats.get('total', 0)

        progress.setRange(0, goal)
        progress.setValue(success)

        # Формат: успешно/цель (всего попыток)
        if total_attempts > success:
            progress.setFormat(f"{success}/{goal} (всего попыток: {total_attempts})")
        else:
            progress.setFormat(f"{success}/{goal}")

        progress.setStyleSheet("""
            QProgressBar {
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 7px;
                background: rgba(0, 0, 0, 0.3);
                text-align: center;
                color: #FFFFFF;
                font-size: 9px;
                font-weight: 700;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3B82F6, stop:1 #8B5CF6);
                border-radius: 6px;
            }
        """)

        layout.addWidget(progress_header)
        layout.addWidget(progress)
        layout.addStretch()

        return widget

    def _create_all_counters_section(self):
        """Создает секцию со всеми счетчиками в одну строку под прогресс-баром"""
        widget = QWidget()
        main_layout = QHBoxLayout(widget)
        main_layout.setContentsMargins(0, 12, 0, 0)  # Увеличили верхний отступ еще больше
        main_layout.setSpacing(2)  # Минимальные промежутки, чтобы максимально использовать пространство

        # Все счетчики в одну строку с понятными подписями
        counters_data = [
            ("✅", self.stats.get('success', 0), "#10B981", "Успешно\nпригласили"),
            ("❌", self.stats.get('errors', 0), "#EF4444", "Ошибок\nвсего"),
            ("👥", self.stats.get('accounts_used', 0), "#3B82F6", "Аккаунтов\nучаствует"),
            ("📊", self.stats.get('total', 0), "#6B7280", "Попыток\nвсего"),
            ("🥶", self.stats.get('frozen', 0), "#6366F1", "Заморожено\nаккаунтов"),
            ("🚫", self.stats.get('spam_blocks', 0), "#F59E0B", "Спам-блоков\nполучено"),
            ("📝", self.stats.get('writeoff', 0), "#8B5CF6", "Списано\nаккаунтов"),
            ("🔒", self.stats.get('privacy', 0), "#EC4899", "Приватных\nограничений"),
            ("⚡", f"{self.stats.get('speed', 0)}/мин", "#22C55E", "Скорость\nинвайтов")
        ]

        for icon, value, color, label_text in counters_data:
            counter = self._create_counter_with_label(icon, value, color, label_text)
            main_layout.addWidget(counter)

        # НЕ добавляем stretch - пусть счетчики занимают всю ширину равномерно

        return widget

    def _create_counter_with_label(self, icon: str, value, color: str, label_text: str) -> QWidget:
        """Создает максимально увеличенный счетчик с огромным местом для чисел"""
        widget = QWidget()
        # МАКСИМАЛЬНО увеличили размеры - теперь счетчики занимают всю доступную область
        widget.setMinimumSize(120, 70)  # Минимальные размеры намного больше
        widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)  # Растягиваются по ширине

        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 5, 8, 5)  # Еще больше отступов
        layout.setSpacing(5)  # Больше расстояние между названием и числом

        # Убрали фон и обводки - виджет прозрачный
        widget.setStyleSheet("""
            QWidget {
                background: transparent;
            }
        """)

        # Верхняя часть: название счетчика (увеличили размер текста)
        label = QLabel(label_text)
        label.setStyleSheet("""
            QLabel {
                font-size: 9px;
                color: rgba(255, 255, 255, 0.7);
                font-weight: 600;
                line-height: 1.2;
            }
        """)
        label.setAlignment(Qt.AlignCenter)
        label.setWordWrap(True)  # Разрешаем перенос строк

        # Нижняя часть: иконка + значение (МАКСИМАЛЬНО увеличили для больших чисел)
        value_layout = QHBoxLayout()
        value_layout.setContentsMargins(0, 0, 0, 0)
        value_layout.setSpacing(8)  # Еще больший промежуток между иконкой и числом
        value_layout.setAlignment(Qt.AlignCenter)

        icon_label = QLabel(icon)
        icon_label.setStyleSheet("font-size: 22px;")  # Увеличили иконку еще больше

        value_label = QLabel(str(value))
        value_label.setStyleSheet(f"""
            QLabel {{
                font-size: 22px;
                color: {color};
                font-weight: 800;
                qproperty-alignment: AlignCenter;
            }}
        """)
        # Устанавливаем минимальную ширину для ОЧЕНЬ больших чисел
        value_label.setMinimumWidth(60)  # Увеличили с 45 до 60
        value_label.setWordWrap(False)  # Запрещаем перенос для чисел
        value_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)  # Растягивается

        value_layout.addWidget(icon_label)
        value_layout.addWidget(value_label)

        layout.addWidget(label)
        layout.addLayout(value_layout)

        # Подсказка при наведении
        tooltip_text = label_text.replace('\n', ' ')
        widget.setToolTip(f"{tooltip_text}: {value}")

        return widget

    # Остальные методы остаются без изменений
    def _create_status_badge(self, icon: str, text: str, color: str) -> QWidget:
        """Создает красивый бейдж статуса (для обратной совместимости)"""
        widget = QWidget()
        widget.setFixedHeight(22)
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(6, 2, 6, 2)
        layout.setSpacing(2)

        widget.setStyleSheet(f"""
            QWidget {{
                background: {color}25;
                border: 1px solid {color}60;
                border-radius: 11px;
            }}
        """)

        icon_label = QLabel(icon)
        icon_label.setStyleSheet("font-size: 11px;")

        text_label = QLabel(text)
        text_label.setStyleSheet(f"""
            font-size: 10px;
            color: {color};
            font-weight: 700;
        """)

        layout.addWidget(icon_label)
        layout.addWidget(text_label)

        return widget

    def _create_stat_badge(self, icon: str, value: str, color: str) -> QWidget:
        """Создает компактный бейдж статистики (для обратной совместимости)"""
        widget = QWidget()
        widget.setFixedWidth(45)
        widget.setFixedHeight(20)
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(4, 1, 4, 1)
        layout.setSpacing(2)

        widget.setStyleSheet(f"""
            QWidget {{
                background: {color}20;
                border: 1px solid {color}40;
                border-radius: 10px;
            }}
        """)

        icon_label = QLabel(icon)
        icon_label.setStyleSheet("font-size: 10px;")

        value_label = QLabel(value)
        value_label.setStyleSheet(f"""
            font-size: 9px;
            color: {color};
            font-weight: 700;
        """)

        layout.addWidget(icon_label)
        layout.addWidget(value_label)

        return widget

class ExpandButton(QPushButton):
    """Компактная кнопка раскрытия/сворачивания"""

    def __init__(self):
        super().__init__()
        self.is_expanded = False
        self.rotation_angle = 0

        self.setFixedSize(24, 24)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("""
            QPushButton {
                background: rgba(59, 130, 246, 0.2);
                border: 1px solid rgba(59, 130, 246, 0.4);
                border-radius: 4px;
            }
            QPushButton:hover {
                background: rgba(59, 130, 246, 0.3);
                border-color: rgba(59, 130, 246, 0.6);
            }
        """)

        self.rotation_animation = QPropertyAnimation(self, b"rotation")
        self.rotation_animation.setDuration(250)
        self.rotation_animation.setEasingCurve(QEasingCurve.OutCubic)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        center = self.rect().center()
        painter.save()
        painter.translate(center)
        painter.rotate(self.rotation_angle)
        painter.translate(-center)

        pen = QPen(QColor(255, 255, 255, 200), 2)
        painter.setPen(pen)

        arrow_size = 4
        x = center.x()
        y = center.y()

        painter.drawLine(x - arrow_size, y - 1, x, y + 2)
        painter.drawLine(x, y + 2, x + arrow_size, y - 1)
        painter.restore()

    def toggle(self):
        self.is_expanded = not self.is_expanded
        self.rotation_animation.setStartValue(self.rotation_angle)
        self.rotation_animation.setEndValue(180 if self.is_expanded else 0)
        self.rotation_animation.start()

    def set_rotation(self, angle):
        self.rotation_angle = angle
        self.update()

    rotation = property(lambda self: self.rotation_angle, set_rotation)


class InviterProfileRow(QWidget):
    """Компактная строка профиля инвайтера с раскрывающейся статистикой чатов"""

    # Сигналы
    profile_started = Signal(str)
    profile_stopped = Signal(str)
    profile_deleted = Signal(str)
    settings_changed = Signal(str, dict)

    def __init__(self, profile_data):
        """ИСПРАВЛЕННЫЙ конструктор с правильным layout"""
        super().__init__()
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.profile_data = profile_data
        self.profile_name = profile_data.get('name', 'Профиль')
        self.is_running = profile_data.get('is_running', False)

        self.users_list = profile_data.get('users_list', [])
        self.chats_list = profile_data.get('chats_list', [])
        self.extended_settings = profile_data.get('extended_settings', {})

        self.process_stats = profile_data.get('process_stats', {})
        self.saved_progress = {
            'success': 0,
            'errors': 0,
            'total_goal': 0,
            'stop_reason': None
        }

        # Флаги и контейнеры для раскрывающейся секции
        self.is_expanded = False
        self.expandable_widget = None
        self.chat_stats_container = None
        self.chat_widgets = []
        self.expand_animation = None
        self.expand_button = None

        self.manually_stopped = False

        self.bot_account = profile_data.get('bot_account', None)
        if not self.bot_account and profile_data.get('config', {}).get('bot_account'):
            self.bot_account = profile_data['config']['bot_account']

        # Таймеры
        self.progress_timer = QTimer()
        self.progress_timer.timeout.connect(self._update_progress_from_module)

        self.completion_timer = QTimer()
        self.completion_timer.timeout.connect(self._check_process_completion)

        self.chat_stats_timer = QTimer()
        self.chat_stats_timer.timeout.connect(self._update_chat_stats)

        self.setObjectName("InviterProfileRow")

        # ВАЖНО: Убираем фиксированную высоту!
        self.setMinimumHeight(85)
        # self.setFixedHeight(85) - убираем это!

        # Инициализация кнопок
        self.users_btn = None
        self.chats_btn = None
        self.settings_btn = None
        self.delete_btn = None
        self.start_stop_btn = None
        self.name_edit = None
        self.invite_type_combo = None
        self.manage_admins_btn = None
        self.bot_token_btn = None

        # ИСПРАВЛЕННЫЙ основной layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 6, 10, 6)
        main_layout.setSpacing(0)  # Убираем промежутки

        # Создаем шапку как отдельный виджет с фиксированной высотой
        self.header_widget = QWidget()
        self.header_widget.setFixedHeight(85)
        self._create_compact_header_content(self.header_widget)

        main_layout.addWidget(self.header_widget)

        # Раскрывающаяся секция добавляется ПОСЛЕ шапки
        self._create_expandable_section(main_layout)

        # Стили
        self._apply_styles()
        self._connect_signals()

        if self.is_running:
            self.progress_timer.start(1000)
            self.completion_timer.start(500)

        QTimer.singleShot(500, self.sync_with_module_state)

    def _create_compact_header_content(self, header_widget):
        """Создает содержимое шапки внутри отдельного виджета"""
        layout = QHBoxLayout(header_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Кнопка раскрытия
        self.expand_button = ExpandButton()
        self.expand_button.clicked.connect(self.toggle_expansion)
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

    def _create_compact_header(self, main_layout):
        """Создает компактную шапку профиля в одну строку"""
        header_widget = QWidget()
        header_widget.setFixedHeight(70)

        layout = QHBoxLayout(header_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Кнопка раскрытия
        self.expand_button = ExpandButton()
        self.expand_button.clicked.connect(self.toggle_expansion)
        layout.addWidget(self.expand_button)

        # Статус индикатор
        status_widget = self._create_compact_status()
        layout.addWidget(status_widget)

        # Кнопка запуска
        start_widget = self._create_compact_start_button()
        layout.addWidget(start_widget)

        # Название профиля
        name_widget = self._create_compact_name()
        layout.addWidget(name_widget)

        # Тип инвайта
        type_widget = self._create_compact_invite_type()
        layout.addWidget(type_widget)

        # Базы
        users_widget = self._create_compact_users_base()
        layout.addWidget(users_widget)

        chats_widget = self._create_compact_chats_base()
        layout.addWidget(chats_widget)

        # Прогресс и статистика
        progress_widget = self._create_inline_progress()
        layout.addWidget(progress_widget)

        # Кнопки управления
        self.control_buttons_widget = self._create_compact_control_buttons()
        layout.addWidget(self.control_buttons_widget)

        main_layout.addWidget(header_widget)

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

    def _create_expandable_section(self, main_layout):
        """Создает раскрывающуюся секцию с обновленными размерами для компактных виджетов"""
        self.expandable_widget = QWidget()
        self.expandable_widget.setMaximumHeight(0)
        self.expandable_widget.setMinimumHeight(0)
        self.expandable_widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

        # Стили для раскрывающейся секции
        self.expandable_widget.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(17, 24, 39, 0.95), stop:1 rgba(31, 41, 55, 0.85));
                border: 1px solid rgba(75, 85, 99, 0.5);
                border-top: 2px solid rgba(59, 130, 246, 0.3);
                border-radius: 0 0 8px 8px;
                margin-left: 10px;
                margin-right: 10px;
                margin-bottom: 4px;
            }
        """)

        layout = QVBoxLayout(self.expandable_widget)
        layout.setContentsMargins(12, 8, 12, 8)  # Уменьшенные отступы
        layout.setSpacing(6)

        # Заголовок секции (более компактный)
        header = QLabel("📊 Детальная статистика по чатам")
        header.setStyleSheet("""
            QLabel {
                font-size: 12px;
                font-weight: 700;
                color: #FFFFFF;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(59, 130, 246, 0.3), stop:1 rgba(139, 92, 246, 0.3));
                padding: 6px 10px;
                border-radius: 4px;
                border: 1px solid rgba(59, 130, 246, 0.4);
                margin-bottom: 4px;
            }
        """)
        layout.addWidget(header)

        # Скроллируемая область с уменьшенной высотой для компактных виджетов
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFixedHeight(140)  # Уменьшили высоту под компактные виджеты (55px каждый)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea {
                background: rgba(0, 0, 0, 0.2);
                border: 1px solid rgba(75, 85, 99, 0.3);
                border-radius: 4px;
            }
            QScrollBar:vertical {
                background: rgba(255, 255, 255, 0.05);
                width: 6px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(59, 130, 246, 0.6), stop:1 rgba(139, 92, 246, 0.6));
                border-radius: 3px;
                min-height: 15px;
            }
            QScrollBar::handle:vertical:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(59, 130, 246, 0.8), stop:1 rgba(139, 92, 246, 0.8));
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        # Контейнер для чатов с уменьшенными отступами
        self.chat_stats_container = QWidget()
        self.chats_layout = QVBoxLayout(self.chat_stats_container)
        self.chats_layout.setContentsMargins(4, 4, 4, 4)  # Уменьшенные отступы
        self.chats_layout.setSpacing(2)  # Минимальные промежутки между виджетами

        scroll.setWidget(self.chat_stats_container)
        layout.addWidget(scroll)

        # Добавляем раскрывающуюся секцию в main_layout
        main_layout.addWidget(self.expandable_widget)

        # Анимация раскрытия
        self.expand_animation = QPropertyAnimation(self.expandable_widget, b"maximumHeight")
        self.expand_animation.setDuration(300)
        self.expand_animation.setEasingCurve(QEasingCurve.OutCubic)

        # Загружаем статистику
        self._load_chat_stats()

    def toggle_expansion(self):
        """Переключение раскрытия с обновленной высотой для компактных виджетов"""
        self.is_expanded = not self.is_expanded
        self.expand_button.toggle()

        if self.is_expanded:
            logger.info(f"📂 Раскрываем статистику для {self.profile_name}")

            # Перезагружаем статистику
            self._load_chat_stats()

            # Высота: заголовок (30px) + скролл (200px) + отступы (24px) = 254px
            target_height = 254

            # Раскрываем
            self.expand_animation.setStartValue(0)
            self.expand_animation.setEndValue(target_height)
            self.expand_animation.start()

            if self.is_running:
                self.chat_stats_timer.start(3000)

        else:
            logger.info(f"📁 Сворачиваем статистику для {self.profile_name}")

            # Сворачиваем
            current_height = self.expandable_widget.maximumHeight()
            self.expand_animation.setStartValue(current_height)
            self.expand_animation.setEndValue(0)
            self.expand_animation.start()

            self.chat_stats_timer.stop()

    def _load_chat_stats(self):
        """Улучшенная загрузка с компактными виджетами"""
        # Очищаем старые виджеты
        for widget in self.chat_widgets:
            widget.deleteLater()
        self.chat_widgets.clear()

        # Получаем статистику
        chats_data = self._get_chats_statistics()

        if not chats_data:
            # Создаем компактную заглушку
            empty_widget = QWidget()
            empty_widget.setFixedHeight(60)
            empty_layout = QVBoxLayout(empty_widget)
            empty_layout.setAlignment(Qt.AlignCenter)
            empty_layout.setSpacing(4)

            empty_widget.setStyleSheet("""
                QWidget {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 rgba(59, 130, 246, 0.1), stop:1 rgba(139, 92, 246, 0.1));
                    border: 2px dashed rgba(59, 130, 246, 0.3);
                    border-radius: 6px;
                    margin: 2px;
                }
            """)

            icon_label = QLabel("📊")
            icon_label.setAlignment(Qt.AlignCenter)
            icon_label.setStyleSheet("font-size: 18px; margin-bottom: 2px;")

            text_label = QLabel("Нет данных по чатам")
            text_label.setAlignment(Qt.AlignCenter)
            text_label.setStyleSheet("""
                color: rgba(255, 255, 255, 0.8);
                font-size: 11px;
                font-weight: 600;
            """)

            hint_label = QLabel("Запустите процесс для отображения статистики")
            hint_label.setAlignment(Qt.AlignCenter)
            hint_label.setStyleSheet("""
                color: rgba(255, 255, 255, 0.5);
                font-size: 9px;
            """)

            empty_layout.addWidget(icon_label)
            empty_layout.addWidget(text_label)
            empty_layout.addWidget(hint_label)

            self.chats_layout.addWidget(empty_widget)
            self.chat_widgets.append(empty_widget)

        else:
            # Создаем компактные виджеты чатов
            for i, (chat_link, stats) in enumerate(chats_data.items()):
                # Используем обновленный ChatStatWidget
                chat_widget = ChatStatWidget(chat_link, stats)
                self.chats_layout.addWidget(chat_widget)
                self.chat_widgets.append(chat_widget)

                # Очень тонкий разделитель между чатами (только если чатов больше 1)
                if i < len(chats_data) - 1:
                    separator = QFrame()
                    separator.setFrameShape(QFrame.HLine)
                    separator.setFixedHeight(1)
                    separator.setStyleSheet("""
                        QFrame {
                            background: rgba(75, 85, 99, 0.15);
                            border: none;
                            margin: 1px 2px;
                        }
                    """)
                    self.chats_layout.addWidget(separator)

        # Добавляем stretch в конце
        self.chats_layout.addStretch()

    def _get_chats_statistics(self) -> Dict:
        """ИСПРАВЛЕННЫЙ метод - правильно распределяет статистику по чатам"""
        try:
            from src.modules.impl.inviter.inviter_manager import _inviter_module_manager

            if _inviter_module_manager and self.profile_name in _inviter_module_manager.active_processes:
                process = _inviter_module_manager.active_processes[self.profile_name]

                # Получаем цель из конфигурации
                goal = 100  # По умолчанию
                if hasattr(process, 'config'):
                    if hasattr(process.config, 'success_per_chat'):
                        goal = process.config.success_per_chat
                    elif isinstance(process.config, dict):
                        goal = process.config.get('success_per_chat', 100)


                chat_stats = {}

                if hasattr(process, 'processed_users') and process.processed_users:
                    from src.entities.moduls.inviter import UserStatus

                    # ПОЛУЧАЕМ СПИСОК ЧАТОВ
                    chat_list = []
                    if hasattr(process, 'chat_threads') and process.chat_threads:
                        chat_list = [thread.chat_link for thread in process.chat_threads if
                                     hasattr(thread, 'chat_link')]
                    elif hasattr(process, 'chats_list') and process.chats_list:
                        chat_list = process.chats_list[:5]
                    elif hasattr(self, 'chats_list'):
                        chat_list = self.chats_list[:3]

                    if not chat_list:
                        logger.warning(f"⚠️ Не найдены чаты для профиля {self.profile_name}")
                        chat_list = ["@test_chat"]

                    # ИНИЦИАЛИЗИРУЕМ СТАТИСТИКУ ДЛЯ КАЖДОГО ЧАТА
                    for chat_link in chat_list:
                        chat_stats[chat_link] = {
                            'success': 0,
                            'privacy': 0,
                            'spam_blocks': 0,
                            'writeoff': 0,
                            'errors': 0,
                            'not_found': 0,
                            'already_in': 0,
                            'flood_wait': 0,
                            'total': 0,
                            'goal': goal,
                            'status': 'active',
                            'accounts_used': 0,
                            'frozen': 0,
                            'speed': 0
                        }

                    # ОСНОВНАЯ ЛОГИКА: РАСПРЕДЕЛЯЕМ ПОЛЬЗОВАТЕЛЕЙ ПО ЧАТАМ

                    for username, user_data in process.processed_users.items():
                        # Определяем к какому чату относится пользователь
                        user_chat = None

                        # Вариант 1: Если в user_data есть информация о чате
                        if hasattr(user_data, 'chat_link'):
                            user_chat = user_data.chat_link
                        elif hasattr(user_data, 'target_chat'):
                            user_chat = user_data.target_chat
                        elif isinstance(user_data, dict):
                            user_chat = user_data.get('chat_link') or user_data.get('target_chat')

                        # Вариант 2: Если не можем определить чат - распределяем равномерно
                        if not user_chat:
                            # Используем хеш от имени пользователя для равномерного распределения
                            import hashlib
                            hash_val = int(hashlib.md5(username.encode()).hexdigest(), 16)
                            chat_index = hash_val % len(chat_list)
                            user_chat = chat_list[chat_index]

                        # Проверяем что чат существует в нашем списке
                        if user_chat not in chat_stats:
                            # Если чата нет в списке, берем первый доступный
                            user_chat = chat_list[0]

                        # ПОДСЧИТЫВАЕМ СТАТИСТИКУ ДЛЯ КОНКРЕТНОГО ЧАТА
                        chat_stats[user_chat]['total'] += 1

                        if hasattr(user_data, 'status'):
                            if user_data.status == UserStatus.INVITED:
                                chat_stats[user_chat]['success'] += 1
                                logger.debug(f"  ✅ {username} → {user_chat}: SUCCESS")
                            elif user_data.status == UserStatus.PRIVACY:
                                chat_stats[user_chat]['privacy'] += 1
                                logger.debug(f"  🔒 {username} → {user_chat}: PRIVACY")
                            elif user_data.status == UserStatus.SPAM_BLOCK:
                                chat_stats[user_chat]['spam_blocks'] += 1
                                logger.debug(f"  🚫 {username} → {user_chat}: SPAM_BLOCK")
                            elif user_data.status == UserStatus.ERROR:
                                chat_stats[user_chat]['writeoff'] += 1
                                logger.debug(f"  ❌ {username} → {user_chat}: ERROR")
                            elif user_data.status == UserStatus.NOT_FOUND:
                                chat_stats[user_chat]['not_found'] += 1
                                logger.debug(f"  👻 {username} → {user_chat}: NOT_FOUND")
                            elif user_data.status == UserStatus.ALREADY_IN:
                                chat_stats[user_chat]['already_in'] += 1
                                logger.debug(f"  👥 {username} → {user_chat}: ALREADY_IN")
                            elif user_data.status == UserStatus.FLOOD_WAIT:
                                chat_stats[user_chat]['flood_wait'] += 1
                                logger.debug(f"  ⏳ {username} → {user_chat}: FLOOD_WAIT")
                            else:
                                chat_stats[user_chat]['errors'] += 1
                                logger.debug(f"  💥 {username} → {user_chat}: OTHER_ERROR")

                    # ДОБАВЛЯЕМ ОБЩУЮ ИНФОРМАЦИЮ ДЛЯ КАЖДОГО ЧАТА
                    total_accounts_used = len(getattr(process, 'finished_successfully_accounts', []))
                    total_frozen = len(getattr(process, 'frozen_accounts', []))

                    for chat_link in chat_stats:
                        # Распределяем общую информацию пропорционально активности чата
                        if chat_stats[chat_link]['total'] > 0:
                            total_activity = sum(stats['total'] for stats in chat_stats.values())
                            if total_activity > 0:
                                activity_ratio = chat_stats[chat_link]['total'] / total_activity
                                chat_stats[chat_link]['accounts_used'] = int(total_accounts_used * activity_ratio)
                                chat_stats[chat_link]['frozen'] = int(total_frozen * activity_ratio)
                            else:
                                chat_stats[chat_link]['accounts_used'] = 0
                                chat_stats[chat_link]['frozen'] = 0

                        # Проверяем статус чата
                        if hasattr(process, 'chat_protection_manager'):
                            if process.chat_protection_manager.is_chat_blocked(chat_link):
                                chat_stats[chat_link]['status'] = 'blocked'

                        if chat_stats[chat_link]['success'] >= chat_stats[chat_link]['goal'] and chat_stats[chat_link][
                            'goal'] > 0:
                            chat_stats[chat_link]['status'] = 'completed'

                        # Рассчитываем скорость
                        if hasattr(process, 'started_at') and process.started_at:
                            from datetime import datetime
                            elapsed = (datetime.now() - process.started_at).total_seconds() / 60
                            if elapsed > 0:
                                chat_stats[chat_link]['speed'] = int(chat_stats[chat_link]['success'] / elapsed)

                    return chat_stats

                # Вариант 2: Если processed_users нет, используем базовую статистику
                elif hasattr(process, 'chat_stats') and process.chat_stats:
                    logger.debug(f"📊 Используем базовую статистику chat_stats")

                    for chat_link, stats in process.chat_stats.items():
                        chat_data = {
                            'success': stats.get('success', 0),
                            'total': stats.get('total', 0),
                            'goal': goal,
                            'status': 'active',
                            'accounts_used': len(getattr(process, 'finished_successfully_accounts', [])),
                            'privacy': stats.get('privacy', 0),
                            'frozen': len(getattr(process, 'frozen_accounts', [])),
                            'writeoff': stats.get('writeoff', 0),
                            'spam_blocks': stats.get('spam_blocks', 0),
                            'errors': stats.get('errors', 0),
                            'speed': 0,
                            'not_found': stats.get('not_found', 0),
                            'already_in': stats.get('already_in', 0),
                            'flood_wait': stats.get('flood_wait', 0)
                        }

                        # Проверяем статус чата
                        if hasattr(process, 'chat_protection_manager'):
                            if process.chat_protection_manager.is_chat_blocked(chat_link):
                                chat_data['status'] = 'blocked'

                        if chat_data['success'] >= chat_data['goal'] and chat_data['goal'] > 0:
                            chat_data['status'] = 'completed'

                        chat_stats[chat_link] = chat_data

                    logger.debug(f"🎯 ВОЗВРАЩАЕМ базовую статистику для {len(chat_stats)} чатов")
                    return chat_stats

                # Вариант 3: Создаем начальную статистику для чатов
                else:
                    logger.debug(f"📝 Создаем начальную статистику из списка чатов")

                    # Берем чаты из разных источников
                    chat_list = []
                    if hasattr(process, 'chat_queue'):
                        # Копируем очередь безопасно
                        temp_queue = []
                        try:
                            while not process.chat_queue.empty():
                                chat = process.chat_queue.get_nowait()
                                chat_list.append(chat)
                                temp_queue.append(chat)
                            # Возвращаем обратно
                            for chat in temp_queue:
                                process.chat_queue.put(chat)
                        except:
                            pass

                    if not chat_list and hasattr(self, 'chats_list'):
                        chat_list = self.chats_list[:3]

                    if not chat_list:
                        chat_list = ["@test_chat"]

                    for chat in chat_list:
                        chat_stats[chat] = {
                            'success': 0,
                            'total': 0,
                            'goal': goal,
                            'status': 'active',
                            'accounts_used': 0,
                            'privacy': 0,
                            'frozen': 0,
                            'writeoff': 0,
                            'spam_blocks': 0,
                            'errors': 0,
                            'speed': 0,
                            'not_found': 0,
                            'already_in': 0,
                            'flood_wait': 0
                        }

                    return chat_stats

            # Если процесс не запущен, создаем статистику на основе списка чатов профиля
            return self._load_stats_from_file()

        except Exception as e:
            logger.error(f"❌ Ошибка получения статистики чатов: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {}

    def _load_stats_from_file(self) -> Dict:
        """Загрузка статистики из файла или создание начальной для чатов профиля"""
        try:
            # Сначала пытаемся найти реальные файлы статистики
            from pathlib import Path
            profile_folder = Path(self.profile_data.get('folder_path', ''))

            # Ищем файлы со статистикой
            stats_files = [
                profile_folder / "chat_statistics.json",
                profile_folder / "Отчеты" / "chat_stats.json",
                profile_folder / "processed_users.json",
            ]

            for stats_file in stats_files:
                if stats_file.exists():
                    logger.debug(f"📁 Загружаем статистику из файла: {stats_file}")
                    import json
                    with open(stats_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if data:
                            return data

            # Если файлов нет, создаем начальную статистику на основе списка чатов
            if self.chats_list:
                initial_stats = {}
                for i, chat in enumerate(self.chats_list[:3]):  # Первые 3 чата
                    initial_stats[chat] = {
                        'success': 0,
                        'total': 0,
                        'goal': 100,
                        'status': 'active',
                        'accounts_used': 0,
                        'privacy': 0,
                        'frozen': 0,
                        'writeoff': 0,
                        'spam_blocks': 0,
                        'errors': 0,
                        'speed': 0,
                        'not_found': 0,
                        'already_in': 0,
                        'flood_wait': 0
                    }
                return initial_stats
            else:
                logger.debug(f"⚠️ Нет чатов в профиле {self.profile_name}")
                return {}

        except Exception as e:
            logger.error(f"❌ Ошибка загрузки статистики из файла: {e}")
            return {}

    def _update_chat_stats(self):
        """Обновляет статистику чатов"""
        if self.is_expanded and self.is_running:

            new_stats = self._get_chats_statistics()

            if new_stats:
                # Если статистика изменилась, пересоздаем виджеты
                if len(new_stats) != len(self.chat_widgets) - 1:  # -1 для заглушки или stretch
                    self._load_chat_stats()
                else:
                    # Обновляем существующие виджеты
                    for widget in self.chat_widgets:
                        if isinstance(widget, ChatStatWidget):
                            if widget.chat_link in new_stats:
                                old_stats = widget.stats
                                new_data = new_stats[widget.chat_link]

                                # Проверяем изменения
                                if old_stats != new_data:
                                    widget.stats = new_data
                                    # Очищаем и пересоздаем layout
                                    while widget.layout().count():
                                        child = widget.layout().takeAt(0)
                                        if child.widget():
                                            child.widget().deleteLater()
                                    widget._create_layout()
                                    logger.debug(f"✅ Обновлен виджет для {widget.chat_link}")

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

    def _on_invite_type_changed_simple(self, new_type: str):
        """Простая смена типа с обновлением кнопок"""
        try:
            logger.debug(f"🔄 Изменен тип инвайта на: {new_type}")

            # Сохраняем тип в конфигурацию
            if new_type == "Через админку":
                self._save_invite_type_settings('admin')
            else:
                self._save_invite_type_settings('classic')

            # Обновляем кнопки управления при смене типа
            self._update_control_buttons_visibility()

        except Exception as e:
            logger.error(f"❌ Ошибка изменения типа инвайта: {e}")

    def _update_control_buttons_visibility(self):
        """Обновляет видимость кнопок управления в зависимости от типа инвайта"""
        try:
            # Пересоздаем виджет кнопок управления
            if hasattr(self, 'control_buttons_widget'):
                # Находим старый виджет в layout
                header_widget = self.findChild(QWidget)
                if header_widget:
                    layout = header_widget.layout()
                    if layout:
                        # Удаляем старый виджет
                        old_widget = self.control_buttons_widget
                        layout.removeWidget(old_widget)
                        old_widget.deleteLater()

                        # Создаем новый с обновленной видимостью кнопок
                        self.control_buttons_widget = self._create_compact_control_buttons()
                        layout.addWidget(self.control_buttons_widget)

                        # Переподключаем сигналы для новых кнопок
                        self._reconnect_control_signals()


        except Exception as e:
            logger.error(f"❌ Ошибка обновления кнопок управления: {e}")

    def _reconnect_control_signals(self):
        """Переподключает сигналы кнопок управления после пересоздания"""
        try:
            # Переподключаем сигналы для кнопок админов и токенов (если они существуют)
            if hasattr(self, 'manage_admins_btn') and self.manage_admins_btn:
                self.manage_admins_btn.clicked.connect(self._on_manage_admins)

            if hasattr(self, 'bot_token_btn') and self.bot_token_btn:
                self.bot_token_btn.clicked.connect(self._on_bot_token_settings)

            # Переподключаем основные кнопки
            if self.settings_btn:
                self.settings_btn.clicked.connect(self._on_extended_settings)

            if self.delete_btn:
                self.delete_btn.clicked.connect(self._delete_profile)

        except Exception as e:
            logger.error(f"❌ Ошибка переподключения сигналов кнопок: {e}")

    def _save_invite_type_settings(self, invite_type: str):
        """Сохраняет настройки типа инвайта"""
        try:
            config_update = {
                'invite_type': invite_type
            }

            # Сохраняем через модуль
            from src.modules.impl.inviter import update_profile_config
            success = update_profile_config(self.profile_name, config_update)

            if success:
                # Обновляем локальные данные
                if 'config' not in self.profile_data:
                    self.profile_data['config'] = {}
                self.profile_data['config'].update(config_update)

                logger.debug(f"✅ Настройки типа инвайта сохранены: {invite_type}")
            else:
                logger.error("❌ Не удалось сохранить настройки типа инвайта")

        except Exception as e:
            logger.error(f"❌ Ошибка сохранения настроек типа инвайта: {e}")

    def _on_name_changed(self):
        """Обработчик изменения имени профиля"""
        if not self.name_edit:
            return

        new_name = self.name_edit.text().strip() or self.profile_name
        if new_name != self.profile_name:
            self.profile_name = new_name
            self.settings_changed.emit(self.profile_name, {'name': new_name})

    def _update_start_button(self):
        """Обновляет текст и цвет кнопки в зависимости от состояния"""
        if not hasattr(self, 'start_stop_btn') or not self.start_stop_btn:
            return

        if self.is_running:
            # Процесс запущен - показываем кнопку "Стоп"
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
            # Процесс не запущен - показываем кнопку "Запуск"
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

    # Методы для обработки кнопок админов и токенов
    def _on_manage_admins(self):
        """Обработчик кнопки управления главными админами"""
        try:
            logger.info(f"👑 Открываем диалог управления админами для профиля: {self.profile_name}")

            from src.modules.impl.inviter.profile_manager import InviterProfileManager
            profile_manager = InviterProfileManager()
            profile_manager.load_all_profiles()
            profile = profile_manager.get_profile(self.profile_name)

            if not profile:
                logger.error(f"❌ Профиль {self.profile_name} не найден")
                return

            # Показываем диалог выбора главных админов
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
            logger.info(f"🤖 Открываем диалог настройки токенов ботов для профиля: {self.profile_name}")

            from gui.dialogs import show_bot_tokens_dialog
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
        """УЛУЧШЕННОЕ переключение состояния профиля"""
        if self.is_running:
            logger.info(f"🛑 Пользователь вручную останавливает профиль: {self.profile_name}")
            self.manually_stopped = True  # Помечаем как ручную остановку
            self.profile_stopped.emit(self.profile_name)
        else:
            logger.info(f"🚀 Пользователь запускает профиль: {self.profile_name}")
            self.manually_stopped = False  # Сбрасываем флаг
            self.profile_started.emit(self.profile_name)

    def update_running_state(self, is_running: bool):
        """УЛУЧШЕННОЕ обновление состояния профиля с правильной логикой кнопки"""
        old_state = self.is_running
        self.is_running = is_running

        logger.debug(f"🔄 Обновляем состояние {self.profile_name}: {old_state} → {is_running}")

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

        # ГЛАВНОЕ: Обновляем кнопку запуска/остановки
        self._update_start_button()

        # Управляем таймерами
        if self.is_running:
            if hasattr(self, 'progress_timer'):
                self.progress_timer.start(1000)
            if hasattr(self, 'completion_timer'):
                self.completion_timer.start(2000)  # Проверяем каждые 2 секунды
            if hasattr(self, 'status_label'):
                self.status_label.setText("🚀 Запущен...")
        else:
            if hasattr(self, 'progress_timer'):
                self.progress_timer.stop()
            if hasattr(self, 'completion_timer'):
                self.completion_timer.stop()
            if hasattr(self, 'chat_stats_timer'):
                self.chat_stats_timer.stop()

            # Обновляем статус в зависимости от причины остановки
            if hasattr(self, 'status_label'):
                if self.manually_stopped:
                    self.status_label.setText("⏹️ Остановлен пользователем")
                else:
                    self.status_label.setText("✅ Работа завершена")

    def _update_progress_from_module(self):
        """Обновляет прогресс-бар из данных модуля"""
        try:
            from src.modules.impl.inviter import get_profile_progress

            progress_data = get_profile_progress(self.profile_name)

            if progress_data:
                total_goal = progress_data.get('total_goal', 0)
                success = progress_data.get('success', 0)
                errors = progress_data.get('errors', 0)

                self.saved_progress['success'] = success
                self.saved_progress['errors'] = errors
                self.saved_progress['total_goal'] = total_goal

                if total_goal > 0:
                    self.progress_bar.setRange(0, total_goal)
                    self.progress_bar.setValue(success)
                    self.progress_bar.setFormat(f"{success}/{total_goal}")

                    self.success_label.setText(f"✅{success}")
                    self.errors_label.setText(f"❌{errors}")

                    speed = progress_data.get('speed', 0)
                    self.speed_label.setText(f"⚡{speed}")

                    status = progress_data.get('status', 'Работает...')
                    if hasattr(self, 'status_label'):
                        self.status_label.setText(status)

                    if success >= total_goal:
                        if hasattr(self, 'status_label'):
                            self.status_label.setText("✅ Цель достигнута!")
                        self.saved_progress['stop_reason'] = "Цель достигнута"

        except Exception as e:
            logger.error(f"❌ Ошибка обновления прогресса для {self.profile_name}: {e}")

    def _check_process_completion(self):
        """УЛУЧШЕННАЯ проверка завершения процесса"""
        try:
            from src.modules.impl.inviter.inviter_manager import _inviter_module_manager

            if not _inviter_module_manager:
                return

            # Проверяем есть ли процесс в активных
            is_actually_running = self.profile_name in _inviter_module_manager.active_processes

            # Если UI показывает что процесс запущен, но в модуле его нет
            if self.is_running and not is_actually_running:
                logger.info(f"🏁 Процесс {self.profile_name} завершен в модуле, обновляем UI")

                # Определяем причину остановки
                if not self.manually_stopped:
                    # Процесс завершился сам (работа выполнена или ошибка)
                    logger.info(f"✅ Процесс {self.profile_name} завершился автоматически")
                    if hasattr(self, 'status_label'):
                        self.status_label.setText("✅ Работа завершена")
                else:
                    # Процесс остановлен вручную
                    logger.info(f"⏹️ Процесс {self.profile_name} остановлен пользователем")
                    if hasattr(self, 'status_label'):
                        self.status_label.setText("⏹️ Остановлен пользователем")

                # Обновляем состояние на "остановлен"
                self.update_running_state(False)

                # Сбрасываем флаг ручной остановки после обработки
                self.manually_stopped = False

        except Exception as e:
            logger.error(f"❌ Ошибка проверки завершения для {self.profile_name}: {e}")

    def sync_with_module_state(self):
        """УЛУЧШЕННАЯ синхронизация состояния с модулем"""
        try:
            from src.modules.impl.inviter.inviter_manager import _inviter_module_manager

            if not _inviter_module_manager:
                return

            # Проверяем реальное состояние в модуле
            is_actually_running = self.profile_name in _inviter_module_manager.active_processes

            # Если состояния не совпадают - исправляем
            if self.is_running != is_actually_running:
                logger.info(
                    f"🔄 ПРИНУДИТЕЛЬНАЯ синхронизация {self.profile_name}: UI={self.is_running}, Module={is_actually_running}")

                # Если модуль говорит что процесс не запущен, а UI показывает запущен
                if self.is_running and not is_actually_running:
                    self.manually_stopped = False  # Это было автоматическое завершение

                self.update_running_state(is_actually_running)

        except Exception as e:
            logger.error(f"❌ Ошибка синхронизации состояния: {e}")

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

    def _load_actual_chats_from_file(self) -> List[str]:
        """Загружает актуальные данные чатов из файла"""
        try:
            from src.modules.impl.inviter import get_profile_chats_from_file

            actual_chats = get_profile_chats_from_file(self.profile_name)

            if actual_chats is not None:
                return actual_chats
            else:
                return getattr(self, 'chats_list', [])

        except Exception as e:
            logger.error(f"❌ Ошибка загрузки чатов из файла для {self.profile_name}: {e}")
            return getattr(self, 'chats_list', [])

    def _on_users_settings(self):
        """Настройка базы пользователей"""
        try:
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


# Класс InviterTableWidget остается без изменений
class InviterTableWidget(QWidget):
    """Основная таблица с профилями инвайтера"""

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

        # Загружаем данные из модуля
        self._load_profiles_from_module()

        # Эффект прозрачности для анимации
        effect = QGraphicsOpacityEffect()
        effect.setOpacity(0.0)
        self.setGraphicsEffect(effect)

        self.sync_timer = QTimer()
        self.sync_timer.timeout.connect(self.force_sync_all_profiles)
        self.sync_timer.start(5000)  # Синхронизация каждые 5 секунд

    def set_parent_manager(self, manager):
        """Устанавливает ссылку на родительский менеджер"""
        self.parent_manager = manager

    def force_sync_all_profiles(self):
        """Принудительная синхронизация всех профилей с модулем"""
        logger.debug("🔄 Принудительная синхронизация всех профилей...")

        for profile_name, profile_row in self.profile_rows.items():
            try:
                profile_row.sync_with_module_state()
            except Exception as e:
                logger.error(f"❌ Ошибка синхронизации {profile_name}: {e}")

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
                row = InviterProfileRow(profile_data)

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
        """УЛУЧШЕННЫЙ запуск профиля"""
        logger.info(f"🚀 Запуск профиля: {profile_name}")

        # СРАЗУ меняем кнопку на "Стоп" и сбрасываем флаг ручной остановки
        if profile_name in self.profile_rows:
            profile_row = self.profile_rows[profile_name]
            profile_row.manually_stopped = False  # Сбрасываем флаг
            profile_row.update_running_state(True)

        # Запускаем в фоне
        import threading
        def start_task():
            try:
                from src.modules.impl.inviter import start_profile
                success = start_profile(profile_name)

                # Если запуск не удался - возвращаем кнопку в "Запуск"
                if not success and profile_name in self.profile_rows:
                    from PySide6.QtCore import QTimer
                    def reset_button():
                        if profile_name in self.profile_rows:
                            self.profile_rows[profile_name].update_running_state(False)
                            if hasattr(self.profile_rows[profile_name], 'status_label'):
                                self.profile_rows[profile_name].status_label.setText("❌ Ошибка запуска")

                    QTimer.singleShot(100, reset_button)

            except Exception as e:
                logger.error(f"❌ Ошибка запуска: {e}")
                # При ошибке возвращаем кнопку в "Запуск"
                if profile_name in self.profile_rows:
                    from PySide6.QtCore import QTimer
                    def reset_button_error():
                        if profile_name in self.profile_rows:
                            self.profile_rows[profile_name].update_running_state(False)
                            if hasattr(self.profile_rows[profile_name], 'status_label'):
                                self.profile_rows[profile_name].status_label.setText("❌ Ошибка запуска")

                    QTimer.singleShot(100, reset_button_error)

        threading.Thread(target=start_task, daemon=True).start()

    def _on_profile_stopped(self, profile_name):
        """УЛУЧШЕННАЯ остановка профиля"""
        logger.info(f"⏸️ Ручная остановка профиля: {profile_name}")

        # Помечаем как ручную остановку ПЕРЕД изменением UI
        if profile_name in self.profile_rows:
            profile_row = self.profile_rows[profile_name]
            profile_row.manually_stopped = True  # Это ручная остановка
            profile_row.update_running_state(False)

        # Останавливаем в фоне
        import threading
        def stop_task():
            try:
                from src.modules.impl.inviter import stop_profile
                result = stop_profile(profile_name)
                logger.info(f"⏹️ Результат остановки {profile_name}: {result}")
            except Exception as e:
                logger.error(f"❌ Ошибка остановки: {e}")

        threading.Thread(target=stop_task, daemon=True).start()


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

        profile_row = InviterProfileRow(profile_data)

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

            profiles_data = get_all_profiles_for_gui()

            self.clear_profiles()

            for profile_data in profiles_data:
                self.add_profile(profile_data)

            logger.info(f"✅ Данные профилей обновлены: {len(profiles_data)} профилей")

        except Exception as e:
            logger.error(f"❌ Ошибка обновления данных профилей: {e}")

    def reload_profiles(self):
        """Перезагружает профили из модуля"""
        try:
            self.clear_profiles()

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