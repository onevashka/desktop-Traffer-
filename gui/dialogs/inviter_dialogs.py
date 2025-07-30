# gui/dialogs/inviter_dialogs.py
"""
Диалоги настроек для инвайтера - ПОЛНАЯ ВЕРСИЯ
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QLineEdit, QSpinBox, QCheckBox, QComboBox,
    QFrame, QScrollArea, QGroupBox, QGridLayout, QGraphicsOpacityEffect,
    QGraphicsDropShadowEffect, QApplication
)
from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve, QRect
from PySide6.QtGui import QFont, QColor
from typing import List, Dict


class UsersBaseDialog(QDialog):
    """Диалог настройки базы пользователей"""

    def __init__(self, parent=None, current_users: List[str] = None):
        super().__init__(parent)
        self.current_users = current_users or []
        self.setWindowTitle("База пользователей")
        self.setModal(True)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(600, 500)
        self.init_ui()
        self._center_on_parent()

    def init_ui(self):
        # Основной контейнер
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Контейнер для контента
        self.content_container = QFrame()
        self.content_container.setObjectName("DialogContainer")
        content_layout = QVBoxLayout(self.content_container)
        content_layout.setContentsMargins(30, 30, 30, 30)
        content_layout.setSpacing(20)

        # Заголовок с иконкой
        header_layout = QHBoxLayout()
        header_layout.setSpacing(15)

        # Иконка
        icon_label = QLabel("📝")
        icon_label.setObjectName("DialogIcon")
        icon_label.setFixedSize(48, 48)
        icon_label.setAlignment(Qt.AlignCenter)

        # Заголовок
        title_label = QLabel("База пользователей")
        title_label.setObjectName("DialogTitle")
        title_label.setWordWrap(True)

        header_layout.addWidget(icon_label)
        header_layout.addWidget(title_label, 1)

        # Описание
        desc = QLabel("Введите username пользователей для инвайта (по одному на строку):")
        desc.setObjectName("DialogDescription")
        desc.setWordWrap(True)

        # Текстовое поле
        self.users_text = QTextEdit()
        self.users_text.setObjectName("UsersTextEdit")
        self.users_text.setPlaceholderText("@username1\n@username2\n@username3\nили без @:\nusername1\nusername2")
        self.users_text.setPlainText('\n'.join(self.current_users))

        # Информация
        info_label = QLabel("💡 Можно вставлять как с @, так и без него")
        info_label.setObjectName("InfoLabel")

        # Кнопки
        buttons_layout = self._create_buttons()

        # Сборка
        content_layout.addLayout(header_layout)
        content_layout.addWidget(desc)
        content_layout.addWidget(self.users_text, 1)
        content_layout.addWidget(info_label)
        content_layout.addLayout(buttons_layout)

        main_layout.addWidget(self.content_container)

        # Стили
        self._apply_styles()

        # Тень
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(30)
        shadow.setXOffset(0)
        shadow.setYOffset(10)
        shadow.setColor(QColor(0, 0, 0, 120))
        self.content_container.setGraphicsEffect(shadow)

    def _create_buttons(self):
        """Создает кнопки диалога"""
        layout = QHBoxLayout()
        layout.setSpacing(12)

        # Кнопка отмены
        cancel_btn = QPushButton("Отменить")
        cancel_btn.setObjectName("CancelButton")
        cancel_btn.setFixedSize(120, 44)
        cancel_btn.clicked.connect(self.reject)

        # Кнопка создания
        create_btn = QPushButton("Создать профиль")
        create_btn.setObjectName("CreateButton")
        create_btn.setFixedSize(150, 44)
        create_btn.clicked.connect(self.accept)

        layout.addStretch()
        layout.addWidget(cancel_btn)
        layout.addWidget(create_btn)

        return layout

    def _center_on_parent(self):
        """Центрирует диалог относительно родителя"""
        if self.parent():
            parent_rect = self.parent().geometry()
            x = parent_rect.x() + (parent_rect.width() - self.width()) // 2
            y = parent_rect.y() + (parent_rect.height() - self.height()) // 2
            self.move(x, y)
        else:
            screen = QApplication.primaryScreen().geometry()
            x = (screen.width() - self.width()) // 2
            y = (screen.height() - self.height()) // 2
            self.move(x, y)

    def _apply_styles(self):
        """Применяет стили к диалогу"""
        self.setStyleSheet("""
            QFrame#DialogContainer {
                background: rgba(20, 20, 20, 0.95);
                border: 2px solid rgba(255, 255, 255, 0.1);
                border-radius: 16px;
                backdrop-filter: blur(20px);
            }

            QLabel#DialogIcon {
                font-size: 32px;
                background: rgba(16, 185, 129, 0.1);
                border-radius: 24px;
                border: 2px solid rgba(16, 185, 129, 0.3);
            }

            QLabel#DialogTitle {
                font-size: 20px;
                font-weight: 700;
                color: #FFFFFF;
                margin: 0;
            }

            QScrollArea#SettingsScroll {
                background: transparent;
                border: none;
            }

            QGroupBox#SettingsGroup {
                font-size: 14px;
                font-weight: 600;
                color: rgba(255, 255, 255, 0.9);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                padding-top: 10px;
                margin-top: 10px;
            }

            QGroupBox#SettingsGroup::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }

            QLabel#SectionLabel {
                font-size: 13px;
                font-weight: 600;
                color: rgba(255, 255, 255, 0.7);
                text-align: center;
                margin: 8px 0;
            }

            QLineEdit#SettingsInput {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 13px;
                color: rgba(255, 255, 255, 0.9);
                selection-background-color: rgba(16, 185, 129, 0.3);
            }

            QLineEdit#SettingsInput:focus {
                border-color: #10B981;
                background: rgba(255, 255, 255, 0.08);
            }

            QComboBox#SettingsCombo {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 13px;
                color: rgba(255, 255, 255, 0.9);
                selection-background-color: rgba(16, 185, 129, 0.3);
            }

            QComboBox#SettingsCombo:focus {
                border-color: #10B981;
                background: rgba(255, 255, 255, 0.08);
            }

            QComboBox#SettingsCombo QAbstractItemView {
                background: rgba(30, 30, 30, 0.95);
                border: 1px solid rgba(255, 255, 255, 0.1);
                selection-background-color: rgba(16, 185, 129, 0.3);
                color: #FFFFFF;
            }

            QSpinBox#SettingsSpinBox {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 6px;
                padding: 8px;
                font-size: 13px;
                color: rgba(255, 255, 255, 0.9);
            }

            QSpinBox#SettingsSpinBox:focus {
                border-color: #10B981;
                background: rgba(255, 255, 255, 0.08);
            }

            QPushButton#SettingsButton {
                background: rgba(59, 130, 246, 0.2);
                border: 1px solid rgba(59, 130, 246, 0.5);
                border-radius: 6px;
                color: #FFFFFF;
                font-size: 13px;
                font-weight: 500;
                padding: 8px 12px;
            }

            QPushButton#SettingsButton:hover {
                background: rgba(59, 130, 246, 0.3);
            }

            QPushButton#CancelButton {
                background: rgba(255, 255, 255, 0.06);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 8px;
                color: rgba(255, 255, 255, 0.9);
                font-size: 14px;
                font-weight: 500;
            }

            QPushButton#CancelButton:hover {
                background: rgba(255, 255, 255, 0.1);
                border-color: rgba(255, 255, 255, 0.3);
                color: #FFFFFF;
            }

            QPushButton#CreateButton {
                background: #10B981;
                border: 1px solid #10B981;
                border-radius: 8px;
                color: #FFFFFF;
                font-size: 14px;
                font-weight: 600;
            }

            QPushButton#CreateButton:hover {
                background: #059669;
                border-color: #059669;
            }
        """)

    def get_profile_data(self) -> Dict:
        """Возвращает данные профиля"""
        return {
            'name': self.profile_name.text() or "Новый профиль",
            'invite_type': self.invite_type.currentText(),
            'threads_per_chat': self.threads_per_chat.value(),
            'chat_limit': self.chat_limit.value(),
            'account_limit': self.account_limit.value(),
            'invite_delay': self.invite_delay.value(),
            'freeze_limit': self.freeze_limit.value(),
            'join_delay': self.join_delay.value(),
            'spam_errors': self.spam_errors.value(),
            'writeoff_limit': self.writeoff_limit.value(),
            'chat_spam_limit': self.chat_spam_limit.value(),
            'chat_writeoff_limit': self.chat_writeoff_limit.value(),
            'unknown_errors_limit': self.unknown_errors_limit.value(),
            'blocked_invites_limit': self.blocked_invites_limit.value(),
            'is_running': False,
            'users_list': [],
            'chats_list': [],
            'extended_settings': {}
        }


class ExtendedSettingsDialog(QDialog):
    """Диалог расширенных настроек профиля"""

    def __init__(self, parent=None, profile_data: Dict = None):
        super().__init__(parent)
        self.profile_data = profile_data or {}
        self.setWindowTitle("Расширенные настройки")
        self.setModal(True)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(600, 700)
        self.init_ui()
        self._center_on_parent()

    def init_ui(self):
        # Основной контейнер
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Контейнер для контента
        self.content_container = QFrame()
        self.content_container.setObjectName("DialogContainer")
        content_layout = QVBoxLayout(self.content_container)
        content_layout.setContentsMargins(30, 30, 30, 30)
        content_layout.setSpacing(20)

        # Заголовок с иконкой
        header_layout = QHBoxLayout()
        header_layout.setSpacing(15)

        # Иконка
        icon_label = QLabel("⚙️")
        icon_label.setObjectName("DialogIcon")
        icon_label.setFixedSize(48, 48)
        icon_label.setAlignment(Qt.AlignCenter)

        # Заголовок
        title_label = QLabel("Расширенные настройки профиля")
        title_label.setObjectName("DialogTitle")
        title_label.setWordWrap(True)

        header_layout.addWidget(icon_label)
        header_layout.addWidget(title_label, 1)

        # Скролл область
        scroll = QScrollArea()
        scroll.setObjectName("SettingsScroll")
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        # Группы настроек
        timing_group = self._create_timing_group()
        scroll_layout.addWidget(timing_group)

        proxy_group = self._create_proxy_group()
        scroll_layout.addWidget(proxy_group)

        advanced_group = self._create_advanced_group()
        scroll_layout.addWidget(advanced_group)

        scroll.setWidget(scroll_widget)
        scroll.setWidgetResizable(True)

        # Кнопки
        buttons_layout = self._create_buttons()

        # Сборка
        content_layout.addLayout(header_layout)
        content_layout.addWidget(scroll, 1)
        content_layout.addLayout(buttons_layout)

        main_layout.addWidget(self.content_container)

        # Стили
        self._apply_styles()

        # Тень
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(30)
        shadow.setXOffset(0)
        shadow.setYOffset(10)
        shadow.setColor(QColor(0, 0, 0, 120))
        self.content_container.setGraphicsEffect(shadow)

    def _create_timing_group(self) -> QGroupBox:
        """Группа настроек тайминга"""
        group = QGroupBox("Настройки времени")
        group.setObjectName("SettingsGroup")
        layout = QGridLayout(group)
        layout.setSpacing(10)

        # Минимальная задержка
        layout.addWidget(QLabel("Мин. задержка (сек):"), 0, 0)
        self.min_delay = QSpinBox()
        self.min_delay.setObjectName("SettingsSpinBox")
        self.min_delay.setRange(1, 3600)
        self.min_delay.setValue(self.profile_data.get('min_delay', 10))
        layout.addWidget(self.min_delay, 0, 1)

        # Максимальная задержка
        layout.addWidget(QLabel("Макс. задержка (сек):"), 1, 0)
        self.max_delay = QSpinBox()
        self.max_delay.setObjectName("SettingsSpinBox")
        self.max_delay.setRange(1, 3600)
        self.max_delay.setValue(self.profile_data.get('max_delay', 60))
        layout.addWidget(self.max_delay, 1, 1)

        # Время работы
        layout.addWidget(QLabel("Время работы (мин):"), 2, 0)
        self.work_time = QSpinBox()
        self.work_time.setObjectName("SettingsSpinBox")
        self.work_time.setRange(1, 1440)  # До 24 часов
        self.work_time.setValue(self.profile_data.get('work_time', 60))
        layout.addWidget(self.work_time, 2, 1)

        # Время отдыха
        layout.addWidget(QLabel("Время отдыха (мин):"), 3, 0)
        self.rest_time = QSpinBox()
        self.rest_time.setObjectName("SettingsSpinBox")
        self.rest_time.setRange(1, 1440)
        self.rest_time.setValue(self.profile_data.get('rest_time', 30))
        layout.addWidget(self.rest_time, 3, 1)

        return group

    def _create_proxy_group(self) -> QGroupBox:
        """Группа настроек прокси"""
        group = QGroupBox("Настройки прокси")
        group.setObjectName("SettingsGroup")
        layout = QVBoxLayout(group)
        layout.setSpacing(10)

        # Использовать прокси
        self.use_proxy = QCheckBox("Использовать прокси")
        self.use_proxy.setObjectName("SettingsCheckBox")
        self.use_proxy.setChecked(self.profile_data.get('use_proxy', False))
        layout.addWidget(self.use_proxy)

        # Автосмена прокси
        self.auto_proxy_change = QCheckBox("Автосмена прокси при ошибках")
        self.auto_proxy_change.setObjectName("SettingsCheckBox")
        self.auto_proxy_change.setChecked(self.profile_data.get('auto_proxy_change', True))
        layout.addWidget(self.auto_proxy_change)

        # Максимальные попытки смены прокси
        proxy_attempts_layout = QHBoxLayout()
        proxy_attempts_layout.addWidget(QLabel("Макс. попыток смены прокси:"))
        self.max_proxy_attempts = QSpinBox()
        self.max_proxy_attempts.setObjectName("SettingsSpinBox")
        self.max_proxy_attempts.setRange(1, 20)
        self.max_proxy_attempts.setValue(self.profile_data.get('max_proxy_attempts', 3))
        proxy_attempts_layout.addWidget(self.max_proxy_attempts)
        layout.addLayout(proxy_attempts_layout)

        return group

    def _create_advanced_group(self) -> QGroupBox:
        """Группа дополнительных настроек"""
        group = QGroupBox("Дополнительные настройки")
        group.setObjectName("SettingsGroup")
        layout = QVBoxLayout(group)
        layout.setSpacing(10)

        # Логирование
        self.enable_logging = QCheckBox("Подробное логирование")
        self.enable_logging.setObjectName("SettingsCheckBox")
        self.enable_logging.setChecked(self.profile_data.get('enable_logging', True))
        layout.addWidget(self.enable_logging)

        # Автоматическая остановка
        self.auto_stop = QCheckBox("Автоостановка при достижении лимитов")
        self.auto_stop.setObjectName("SettingsCheckBox")
        self.auto_stop.setChecked(self.profile_data.get('auto_stop', True))
        layout.addWidget(self.auto_stop)

        # Уведомления
        self.notifications = QCheckBox("Показывать уведомления")
        self.notifications.setObjectName("SettingsCheckBox")
        self.notifications.setChecked(self.profile_data.get('notifications', True))
        layout.addWidget(self.notifications)

        # Сохранение логов в файл
        self.save_logs = QCheckBox("Сохранять логи в файл")
        self.save_logs.setObjectName("SettingsCheckBox")
        self.save_logs.setChecked(self.profile_data.get('save_logs', False))
        layout.addWidget(self.save_logs)

        # Автоматический перезапуск
        self.auto_restart = QCheckBox("Автоматический перезапуск после ошибок")
        self.auto_restart.setObjectName("SettingsCheckBox")
        self.auto_restart.setChecked(self.profile_data.get('auto_restart', False))
        layout.addWidget(self.auto_restart)

        return group

    def _create_buttons(self):
        """Создает кнопки диалога"""
        layout = QHBoxLayout()
        layout.setSpacing(12)

        # Кнопка отмены
        cancel_btn = QPushButton("Отменить")
        cancel_btn.setObjectName("CancelButton")
        cancel_btn.setFixedSize(120, 44)
        cancel_btn.clicked.connect(self.reject)

        # Кнопка сохранения
        save_btn = QPushButton("Сохранить")
        save_btn.setObjectName("SaveButton")
        save_btn.setFixedSize(120, 44)
        save_btn.clicked.connect(self.accept)

        layout.addStretch()
        layout.addWidget(cancel_btn)
        layout.addWidget(save_btn)

        return layout

    def _center_on_parent(self):
        """Центрирует диалог относительно родителя"""
        if self.parent():
            parent_rect = self.parent().geometry()
            x = parent_rect.x() + (parent_rect.width() - self.width()) // 2
            y = parent_rect.y() + (parent_rect.height() - self.height()) // 2
            self.move(x, y)
        else:
            screen = QApplication.primaryScreen().geometry()
            x = (screen.width() - self.width()) // 2
            y = (screen.height() - self.height()) // 2
            self.move(x, y)

    def _apply_styles(self):
        """Применяет стили к диалогу"""
        self.setStyleSheet("""
            QFrame#DialogContainer {
                background: rgba(20, 20, 20, 0.95);
                border: 2px solid rgba(255, 255, 255, 0.1);
                border-radius: 16px;
                backdrop-filter: blur(20px);
            }

            QLabel#DialogIcon {
                font-size: 32px;
                background: rgba(156, 163, 175, 0.1);
                border-radius: 24px;
                border: 2px solid rgba(156, 163, 175, 0.3);
            }

            QLabel#DialogTitle {
                font-size: 20px;
                font-weight: 700;
                color: #FFFFFF;
                margin: 0;
            }

            QScrollArea#SettingsScroll {
                background: transparent;
                border: none;
            }

            QGroupBox#SettingsGroup {
                font-size: 14px;
                font-weight: 600;
                color: rgba(255, 255, 255, 0.9);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                padding-top: 10px;
                margin-top: 10px;
            }

            QGroupBox#SettingsGroup::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }

            QSpinBox#SettingsSpinBox {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 6px;
                padding: 8px;
                font-size: 13px;
                color: rgba(255, 255, 255, 0.9);
            }

            QSpinBox#SettingsSpinBox:focus {
                border-color: #9CA3AF;
                background: rgba(255, 255, 255, 0.08);
            }

            QCheckBox#SettingsCheckBox {
                color: rgba(255, 255, 255, 0.9);
                font-size: 13px;
                font-weight: 500;
                spacing: 8px;
            }

            QCheckBox#SettingsCheckBox::indicator {
                width: 18px;
                height: 18px;
            }

            QCheckBox#SettingsCheckBox::indicator:unchecked {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 4px;
            }

            QCheckBox#SettingsCheckBox::indicator:checked {
                background: #9CA3AF;
                border: 1px solid #9CA3AF;
                border-radius: 4px;
            }

            QPushButton#CancelButton {
                background: rgba(255, 255, 255, 0.06);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 8px;
                color: rgba(255, 255, 255, 0.9);
                font-size: 14px;
                font-weight: 500;
            }

            QPushButton#CancelButton:hover {
                background: rgba(255, 255, 255, 0.1);
                border-color: rgba(255, 255, 255, 0.3);
                color: #FFFFFF;
            }

            QPushButton#SaveButton {
                background: #9CA3AF;
                border: 1px solid #9CA3AF;
                border-radius: 8px;
                color: #FFFFFF;
                font-size: 14px;
                font-weight: 600;
            }

            QPushButton#SaveButton:hover {
                background: #6B7280;
                border-color: #6B7280;
            }
        """)

    def get_settings(self) -> Dict:
        """Возвращает настройки"""
        return {
            'min_delay': self.min_delay.value(),
            'max_delay': self.max_delay.value(),
            'work_time': self.work_time.value(),
            'rest_time': self.rest_time.value(),
            'use_proxy': self.use_proxy.isChecked(),
            'auto_proxy_change': self.auto_proxy_change.isChecked(),
            'max_proxy_attempts': self.max_proxy_attempts.value(),
            'enable_logging': self.enable_logging.isChecked(),
            'auto_stop': self.auto_stop.isChecked(),
            'notifications': self.notifications.isChecked(),
            'save_logs': self.save_logs.isChecked(),
            'auto_restart': self.auto_restart.isChecked()
        }


# Удобные функции для показа диалогов
def show_users_base_dialog(parent, current_users: List[str] = None) -> List[str]:
    """Показывает диалог настройки базы пользователей"""
    dialog = UsersBaseDialog(parent, current_users)
    if dialog.exec() == QDialog.Accepted:
        return dialog.get_users()
    return current_users or []


def show_chats_base_dialog(parent, current_chats: List[str] = None) -> List[str]:
    """Показывает диалог настройки базы чатов"""
    dialog = ChatsBaseDialog(parent, current_chats)
    if dialog.exec() == QDialog.Accepted:
        return dialog.get_chats()
    return current_chats or []


def show_create_profile_dialog(parent) -> Dict:
    """Показывает диалог создания профиля"""
    dialog = CreateProfileDialog(parent)
    if dialog.exec() == QDialog.Accepted:
        return dialog.get_profile_data()
    return {}


def show_extended_settings_dialog(parent, profile_data: Dict = None) -> Dict:
    """Показывает диалог расширенных настроек"""
    dialog = ExtendedSettingsDialog(parent, profile_data)
    if dialog.exec() == QDialog.Accepted:
        return dialog.get_settings()
    return profile_data or {}

    # Кнопка отмены
    cancel_btn = QPushButton("Отменить")
    cancel_btn.setObjectName("CancelButton")
    cancel_btn.setFixedSize(120, 44)
    cancel_btn.clicked.connect(self.reject)

    # Кнопка сохранения
    save_btn = QPushButton("Сохранить")
    save_btn.setObjectName("SaveButton")
    save_btn.setFixedSize(120, 44)
    save_btn.clicked.connect(self.accept)

    layout.addStretch()
    layout.addWidget(cancel_btn)
    layout.addWidget(save_btn)

    return layout


def _center_on_parent(self):
    """Центрирует диалог относительно родителя"""
    if self.parent():
        parent_rect = self.parent().geometry()
        x = parent_rect.x() + (parent_rect.width() - self.width()) // 2
        y = parent_rect.y() + (parent_rect.height() - self.height()) // 2
        self.move(x, y)
    else:
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)


def _apply_styles(self):
    """Применяет стили к диалогу"""
    self.setStyleSheet("""
            QFrame#DialogContainer {
                background: rgba(20, 20, 20, 0.95);
                border: 2px solid rgba(255, 255, 255, 0.1);
                border-radius: 16px;
                backdrop-filter: blur(20px);
            }

            QLabel#DialogIcon {
                font-size: 32px;
                background: rgba(59, 130, 246, 0.1);
                border-radius: 24px;
                border: 2px solid rgba(59, 130, 246, 0.3);
            }

            QLabel#DialogTitle {
                font-size: 20px;
                font-weight: 700;
                color: #FFFFFF;
                margin: 0;
            }

            QLabel#DialogDescription {
                font-size: 14px;
                color: rgba(255, 255, 255, 0.8);
                line-height: 1.4;
                margin: 0;
            }

            QTextEdit#UsersTextEdit {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                padding: 12px;
                font-family: 'Consolas', monospace;
                font-size: 13px;
                color: rgba(255, 255, 255, 0.9);
                selection-background-color: rgba(59, 130, 246, 0.3);
            }

            QTextEdit#UsersTextEdit:focus {
                border-color: #3B82F6;
                background: rgba(255, 255, 255, 0.08);
            }

            QLabel#InfoLabel {
                font-size: 12px;
                color: rgba(59, 130, 246, 0.8);
                background: rgba(59, 130, 246, 0.05);
                border: 1px solid rgba(59, 130, 246, 0.2);
                border-radius: 6px;
                padding: 8px;
                margin: 0;
            }

            QPushButton#CancelButton {
                background: rgba(255, 255, 255, 0.06);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 8px;
                color: rgba(255, 255, 255, 0.9);
                font-size: 14px;
                font-weight: 500;
            }

            QPushButton#CancelButton:hover {
                background: rgba(255, 255, 255, 0.1);
                border-color: rgba(255, 255, 255, 0.3);
                color: #FFFFFF;
            }

            QPushButton#SaveButton {
                background: #10B981;
                border: 1px solid #10B981;
                border-radius: 8px;
                color: #FFFFFF;
                font-size: 14px;
                font-weight: 600;
            }

            QPushButton#SaveButton:hover {
                background: #059669;
                border-color: #059669;
            }
        """)


def get_users(self) -> List[str]:
    """Возвращает список пользователей"""
    text = self.users_text.toPlainText()
    users = []
    for line in text.split('\n'):
        line = line.strip()
        if line:
            # Убираем @ если есть
            if line.startswith('@'):
                line = line[1:]
            if line:  # Проверяем что что-то осталось
                users.append(line)
    return users


class ChatsBaseDialog(QDialog):
    """Диалог настройки базы чатов"""

    def __init__(self, parent=None, current_chats: List[str] = None):
        super().__init__(parent)
        self.current_chats = current_chats or []
        self.setWindowTitle("База чатов")
        self.setModal(True)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(600, 500)
        self.init_ui()
        self._center_on_parent()

    def init_ui(self):
        # Основной контейнер
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Контейнер для контента
        self.content_container = QFrame()
        self.content_container.setObjectName("DialogContainer")
        content_layout = QVBoxLayout(self.content_container)
        content_layout.setContentsMargins(30, 30, 30, 30)
        content_layout.setSpacing(20)

        # Заголовок с иконкой
        header_layout = QHBoxLayout()
        header_layout.setSpacing(15)

        # Иконка
        icon_label = QLabel("💬")
        icon_label.setObjectName("DialogIcon")
        icon_label.setFixedSize(48, 48)
        icon_label.setAlignment(Qt.AlignCenter)

        # Заголовок
        title_label = QLabel("База чатов")
        title_label.setObjectName("DialogTitle")
        title_label.setWordWrap(True)

        header_layout.addWidget(icon_label)
        header_layout.addWidget(title_label, 1)

        # Описание
        desc = QLabel("Введите ссылки на чаты/каналы для инвайта (по одной на строку):")
        desc.setObjectName("DialogDescription")
        desc.setWordWrap(True)

        # Текстовое поле
        self.chats_text = QTextEdit()
        self.chats_text.setObjectName("ChatsTextEdit")
        self.chats_text.setPlaceholderText(
            "https://t.me/chat1\nt.me/channel2\n@chatusername\nhttps://t.me/joinchat/ABC123")
        self.chats_text.setPlainText('\n'.join(self.current_chats))

        # Информация
        info_label = QLabel("💡 Поддерживаются: полные ссылки, короткие ссылки, @username, invite ссылки")
        info_label.setObjectName("InfoLabel")

        # Кнопки
        buttons_layout = self._create_buttons()

        # Сборка
        content_layout.addLayout(header_layout)
        content_layout.addWidget(desc)
        content_layout.addWidget(self.chats_text, 1)
        content_layout.addWidget(info_label)
        content_layout.addLayout(buttons_layout)

        main_layout.addWidget(self.content_container)

        # Стили
        self._apply_styles()

        # Тень
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(30)
        shadow.setXOffset(0)
        shadow.setYOffset(10)
        shadow.setColor(QColor(0, 0, 0, 120))
        self.content_container.setGraphicsEffect(shadow)

    def _create_buttons(self):
        """Создает кнопки диалога"""
        layout = QHBoxLayout()
        layout.setSpacing(12)

        # Кнопка отмены
        cancel_btn = QPushButton("Отменить")
        cancel_btn.setObjectName("CancelButton")
        cancel_btn.setFixedSize(120, 44)
        cancel_btn.clicked.connect(self.reject)

        # Кнопка сохранения
        save_btn = QPushButton("Сохранить")
        save_btn.setObjectName("SaveButton")
        save_btn.setFixedSize(120, 44)
        save_btn.clicked.connect(self.accept)

        layout.addStretch()
        layout.addWidget(cancel_btn)
        layout.addWidget(save_btn)

        return layout

    def _center_on_parent(self):
        """Центrирует диалог относительно родителя"""
        if self.parent():
            parent_rect = self.parent().geometry()
            x = parent_rect.x() + (parent_rect.width() - self.width()) // 2
            y = parent_rect.y() + (parent_rect.height() - self.height()) // 2
            self.move(x, y)
        else:
            screen = QApplication.primaryScreen().geometry()
            x = (screen.width() - self.width()) // 2
            y = (screen.height() - self.height()) // 2
            self.move(x, y)

    def _apply_styles(self):
        """Применяет стили к диалогу"""
        self.setStyleSheet("""
            QFrame#DialogContainer {
                background: rgba(20, 20, 20, 0.95);
                border: 2px solid rgba(255, 255, 255, 0.1);
                border-radius: 16px;
                backdrop-filter: blur(20px);
            }

            QLabel#DialogIcon {
                font-size: 32px;
                background: rgba(16, 185, 129, 0.1);
                border-radius: 24px;
                border: 2px solid rgba(16, 185, 129, 0.3);
            }

            QLabel#DialogTitle {
                font-size: 20px;
                font-weight: 700;
                color: #FFFFFF;
                margin: 0;
            }

            QLabel#DialogDescription {
                font-size: 14px;
                color: rgba(255, 255, 255, 0.8);
                line-height: 1.4;
                margin: 0;
            }

            QTextEdit#ChatsTextEdit {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                padding: 12px;
                font-family: 'Consolas', monospace;
                font-size: 13px;
                color: rgba(255, 255, 255, 0.9);
                selection-background-color: rgba(16, 185, 129, 0.3);
            }

            QTextEdit#ChatsTextEdit:focus {
                border-color: #10B981;
                background: rgba(255, 255, 255, 0.08);
            }

            QLabel#InfoLabel {
                font-size: 12px;
                color: rgba(16, 185, 129, 0.8);
                background: rgba(16, 185, 129, 0.05);
                border: 1px solid rgba(16, 185, 129, 0.2);
                border-radius: 6px;
                padding: 8px;
                margin: 0;
            }

            QPushButton#CancelButton {
                background: rgba(255, 255, 255, 0.06);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 8px;
                color: rgba(255, 255, 255, 0.9);
                font-size: 14px;
                font-weight: 500;
            }

            QPushButton#CancelButton:hover {
                background: rgba(255, 255, 255, 0.1);
                border-color: rgba(255, 255, 255, 0.3);
                color: #FFFFFF;
            }

            QPushButton#SaveButton {
                background: #10B981;
                border: 1px solid #10B981;
                border-radius: 8px;
                color: #FFFFFF;
                font-size: 14px;
                font-weight: 600;
            }

            QPushButton#SaveButton:hover {
                background: #059669;
                border-color: #059669;
            }
        """)

    def get_chats(self) -> List[str]:
        """Возвращает список чатов"""
        text = self.chats_text.toPlainText()
        chats = []
        for line in text.split('\n'):
            line = line.strip()
            if line:
                chats.append(line)
        return chats


class CreateProfileDialog(QDialog):
    """Диалог создания нового профиля инвайтера"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Создать профиль инвайтера")
        self.setModal(True)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(700, 800)
        self.init_ui()
        self._center_on_parent()

    def init_ui(self):
        # Основной контейнер
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Контейнер для контента
        self.content_container = QFrame()
        self.content_container.setObjectName("DialogContainer")
        content_layout = QVBoxLayout(self.content_container)
        content_layout.setContentsMargins(30, 30, 30, 30)
        content_layout.setSpacing(20)

        # Заголовок с иконкой
        header_layout = QHBoxLayout()
        header_layout.setSpacing(15)

        # Иконка
        icon_label = QLabel("➕")
        icon_label.setObjectName("DialogIcon")
        icon_label.setFixedSize(48, 48)
        icon_label.setAlignment(Qt.AlignCenter)

        # Заголовок
        title_label = QLabel("Создание нового профиля")
        title_label.setObjectName("DialogTitle")
        title_label.setWordWrap(True)

        header_layout.addWidget(icon_label)
        header_layout.addWidget(title_label, 1)

        # Скролл область для настроек
        scroll = QScrollArea()
        scroll.setObjectName("SettingsScroll")
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        # Основные настройки
        basic_group = self._create_basic_settings_group()
        scroll_layout.addWidget(basic_group)

        # Настройки работы
        work_group = self._create_work_settings_group()
        scroll_layout.addWidget(work_group)

        # Настройки безопасности
        security_group = self._create_security_settings_group()
        scroll_layout.addWidget(security_group)

        scroll.setWidget(scroll_widget)
        scroll.setWidgetResizable(True)

        # Кнопки
        buttons_layout = self._create_buttons()

        # Сборка
        content_layout.addLayout(header_layout)
        content_layout.addWidget(scroll, 1)
        content_layout.addLayout(buttons_layout)

        main_layout.addWidget(self.content_container)

        # Стили
        self._apply_styles()

        # Тень
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(30)
        shadow.setXOffset(0)
        shadow.setYOffset(10)
        shadow.setColor(QColor(0, 0, 0, 120))
        self.content_container.setGraphicsEffect(shadow)

    def _create_basic_settings_group(self) -> QGroupBox:
        """Создает группу основных настроек"""
        group = QGroupBox("Основные настройки")
        group.setObjectName("SettingsGroup")
        layout = QGridLayout(group)
        layout.setSpacing(10)

        # Название профиля
        layout.addWidget(QLabel("Название профиля:"), 0, 0)
        self.profile_name = QLineEdit()
        self.profile_name.setObjectName("SettingsInput")
        self.profile_name.setPlaceholderText("Введите название профиля")
        layout.addWidget(self.profile_name, 0, 1)

        # Тип инвайта
        layout.addWidget(QLabel("Тип инвайта:"), 1, 0)
        self.invite_type = QComboBox()
        self.invite_type.setObjectName("SettingsCombo")
        self.invite_type.addItems(["Классический", "Через админку"])
        layout.addWidget(self.invite_type, 1, 1)

        # Выбор аккаунтов
        layout.addWidget(QLabel("Аккаунты:"), 2, 0)
        self.accounts_btn = QPushButton("Выбрать аккаунты")
        self.accounts_btn.setObjectName("SettingsButton")
        layout.addWidget(self.accounts_btn, 2, 1)

        return group

    def _create_work_settings_group(self) -> QGroupBox:
        """Создает группу настроек работы"""
        group = QGroupBox("Настройки работы")
        group.setObjectName("SettingsGroup")
        layout = QGridLayout(group)
        layout.setSpacing(10)

        # Потоков на чат
        layout.addWidget(QLabel("Потоков на чат:"), 0, 0)
        self.threads_per_chat = QSpinBox()
        self.threads_per_chat.setObjectName("SettingsSpinBox")
        self.threads_per_chat.setRange(1, 10)
        self.threads_per_chat.setValue(2)
        layout.addWidget(self.threads_per_chat, 0, 1)

        # Лимит инвайтов на чат
        layout.addWidget(QLabel("Лимит на чат:"), 1, 0)
        self.chat_limit = QSpinBox()
        self.chat_limit.setObjectName("SettingsSpinBox")
        self.chat_limit.setRange(1, 1000)
        self.chat_limit.setValue(50)
        layout.addWidget(self.chat_limit, 1, 1)

        # Лимит инвайтов на аккаунт
        layout.addWidget(QLabel("Лимит на аккаунт:"), 2, 0)
        self.account_limit = QSpinBox()
        self.account_limit.setObjectName("SettingsSpinBox")
        self.account_limit.setRange(1, 1000)
        self.account_limit.setValue(100)
        layout.addWidget(self.account_limit, 2, 1)

        # Задержка между инвайтами
        layout.addWidget(QLabel("Задержка (сек):"), 3, 0)
        self.invite_delay = QSpinBox()
        self.invite_delay.setObjectName("SettingsSpinBox")
        self.invite_delay.setRange(1, 300)
        self.invite_delay.setValue(30)
        layout.addWidget(self.invite_delay, 3, 1)

        # Глобальный лимит заморозки
        layout.addWidget(QLabel("Лимит заморозки:"), 4, 0)
        self.freeze_limit = QSpinBox()
        self.freeze_limit.setObjectName("SettingsSpinBox")
        self.freeze_limit.setRange(1, 100)
        self.freeze_limit.setValue(5)
        layout.addWidget(self.freeze_limit, 4, 1)

        # Задержка после вступления
        layout.addWidget(QLabel("Задержка после вступления (сек):"), 5, 0)
        self.join_delay = QSpinBox()
        self.join_delay.setObjectName("SettingsSpinBox")
        self.join_delay.setRange(1, 3600)
        self.join_delay.setValue(300)
        layout.addWidget(self.join_delay, 5, 1)

        return group

    def _create_security_settings_group(self) -> QGroupBox:
        """Создает группу настроек безопасности"""
        group = QGroupBox("Настройки безопасности")
        group.setObjectName("SettingsGroup")
        layout = QGridLayout(group)
        layout.setSpacing(10)

        # Заголовок блока защиты аккаунта
        account_label = QLabel("=== Защита аккаунта ===")
        account_label.setObjectName("SectionLabel")
        layout.addWidget(account_label, 0, 0, 1, 2)

        # Ошибок спамблока до остановки
        layout.addWidget(QLabel("Спамблоков до остановки:"), 1, 0)
        self.spam_errors = QSpinBox()
        self.spam_errors.setObjectName("SettingsSpinBox")
        self.spam_errors.setRange(1, 50)
        self.spam_errors.setValue(3)
        layout.addWidget(self.spam_errors, 1, 1)

        # Списаний до остановки
        layout.addWidget(QLabel("Списаний до остановки:"), 2, 0)
        self.writeoff_limit = QSpinBox()
        self.writeoff_limit.setObjectName("SettingsSpinBox")
        self.writeoff_limit.setRange(1, 20)
        self.writeoff_limit.setValue(2)
        layout.addWidget(self.writeoff_limit, 2, 1)

        # Заголовок блока защиты чата
        chat_label = QLabel("=== Защита чата ===")
        chat_label.setObjectName("SectionLabel")
        layout.addWidget(chat_label, 3, 0, 1, 2)

        # Спамблоков подряд
        layout.addWidget(QLabel("Спамблоков подряд:"), 4, 0)
        self.chat_spam_limit = QSpinBox()
        self.chat_spam_limit.setObjectName("SettingsSpinBox")
        self.chat_spam_limit.setRange(1, 20)
        self.chat_spam_limit.setValue(3)
        layout.addWidget(self.chat_spam_limit, 4, 1)

        # Списаний подряд
        layout.addWidget(QLabel("Списаний подряд:"), 5, 0)
        self.chat_writeoff_limit = QSpinBox()
        self.chat_writeoff_limit.setObjectName("SettingsSpinBox")
        self.chat_writeoff_limit.setRange(1, 10)
        self.chat_writeoff_limit.setValue(2)
        layout.addWidget(self.chat_writeoff_limit, 5, 1)

        # Неизвестных ошибок подряд
        layout.addWidget(QLabel("Неизвестных ошибок подряд:"), 6, 0)
        self.unknown_errors_limit = QSpinBox()
        self.unknown_errors_limit.setObjectName("SettingsSpinBox")
        self.unknown_errors_limit.setRange(1, 20)
        self.unknown_errors_limit.setValue(5)
        layout.addWidget(self.unknown_errors_limit, 6, 1)

        # Заблокированных инвайтов подряд
        layout.addWidget(QLabel("Заблокированных подряд:"), 7, 0)
        self.blocked_invites_limit = QSpinBox()
        self.blocked_invites_limit.setObjectName("SettingsSpinBox")
        self.blocked_invites_limit.setRange(1, 20)
        self.blocked_invites_limit.setValue(3)
        layout.addWidget(self.blocked_invites_limit, 7, 1)

        return group

    def _create_buttons(self):
        """Создает кнопки диалога"""
        layout = QHBoxLayout()
        layout