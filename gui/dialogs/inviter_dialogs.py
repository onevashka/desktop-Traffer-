# gui/dialogs/inviter_dialogs.py - ИСПРАВЛЕННАЯ ВЕРСИЯ
"""
Диалоги настроек для инвайтера - ПОЛНАЯ ВЕРСИЯ
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QLineEdit, QSpinBox, QCheckBox, QComboBox,
    QFrame, QScrollArea, QGroupBox, QGridLayout, QGraphicsOpacityEffect,
    QGraphicsDropShadowEffect, QApplication, QWidget
)
from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve, QRect,  QTimer
from PySide6.QtGui import QFont, QColor
from typing import List, Dict
from loguru import logger

from gui.dialogs.main_admins_dialog import show_main_admins_dialog
from gui.dialogs.bot_token_dialog import show_bot_token_dialog, load_bot_token_from_profile



class UsersBaseDialog(QDialog):
    """Диалог настройки базы пользователей"""

    def __init__(self, parent=None, current_users: List[str] = None):
        super().__init__(parent)
        self.current_users = current_users or []
        self.setWindowTitle("База пользователей")
        self.setModal(True)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(1400, 1200)
        self.init_ui()
        QTimer.singleShot(0, self._center_on_parent)


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

        # Кнопка сохранения
        save_btn = QPushButton("Сохранить")
        save_btn.setObjectName("SaveButton")
        save_btn.setFixedSize(120, 44)
        save_btn.clicked.connect(self.accept)

        layout.addStretch()
        layout.addWidget(cancel_btn)
        layout.addWidget(save_btn)

        return layout

    def showEvent(self, event):
        super().showEvent(event)
        self._center_on_parent()

    def _center_on_parent(self):
        """Центрируем диалог над top-level окном родителя, или по центру экрана."""
        # Если есть родитель, берём его top-level окно (чтобы geometry был валидным)
        parent = self.parent()
        if parent:
            parent = parent.window()
        # Вычисляем прямоугольник, над которым будем центрировать
        if isinstance(parent, QWidget):
            target_rect = parent.frameGeometry()
        else:
            target_rect = QApplication.primaryScreen().geometry()
        # Центр этого прямоугольника
        center_point = target_rect.center()
        # Сдвигаем левый-верхний угол диалога так, чтобы его центр совпал с центром target
        self.move(center_point.x() - self.width() // 2,
                  center_point.y() - self.height() // 2)

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
        self.setFixedSize(1400, 1200)
        self.init_ui()
        QTimer.singleShot(0, self._center_on_parent)

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
        """Центрируем диалог над top-level окном родителя, или по центру экрана."""
        # Если есть родитель, берём его top-level окно (чтобы geometry был валидным)
        parent = self.parent()
        if parent:
            parent = parent.window()
        # Вычисляем прямоугольник, над которым будем центрировать
        if isinstance(parent, QWidget):
            target_rect = parent.frameGeometry()
        else:
            target_rect = QApplication.primaryScreen().geometry()
        # Центр этого прямоугольника
        center_point = target_rect.center()
        # Сдвигаем левый-верхний угол диалога так, чтобы его центр совпал с центром target
        self.move(center_point.x() - self.width() // 2,
                  center_point.y() - self.height() // 2)

    def showEvent(self, event):
        super().showEvent(event)
        self._center_on_parent()

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


class ExtendedSettingsDialog(QDialog):
    """Диалог расширенных настроек профиля"""

    def __init__(self, parent=None, current_settings: Dict = None):
        super().__init__(parent)
        self.current_settings = current_settings or {}
        self.setWindowTitle("Расширенные настройки")
        self.setModal(True)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(1100, 900)
        self.init_ui()
        QTimer.singleShot(0, self._center_on_parent)

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
        main_group = self._create_main_settings_group()
        acc_sec_group = self._create_account_security_group()
        chat_sec_group = self._create_chat_security_group()

        scroll_layout.addWidget(main_group)
        scroll_layout.addWidget(acc_sec_group)
        scroll_layout.addWidget(chat_sec_group)

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

    def showEvent(self, event):
        super().showEvent(event)
        self._center_on_parent()

    def _create_main_settings_group(self) -> QGroupBox:
        group = QGroupBox("Основные параметры работы")
        layout = QGridLayout(group)
        layout.setSpacing(10)

        # 1) Количество одновременных потоков в одном чате
        layout.addWidget(QLabel("Потоков на каждый чат:"), 0, 0)
        self.threads_per_chat = QSpinBox()
        self.threads_per_chat.setRange(1, 50)
        self.threads_per_chat.setValue(self.current_settings.get('threads_per_chat', 2))
        layout.addWidget(self.threads_per_chat, 0, 1)

        # 2) Максимум успешных приглашений в одном чате
        layout.addWidget(QLabel("Максимум успешных приглашений на чат:"), 1, 0)
        self.success_per_chat = QSpinBox()
        self.success_per_chat.setRange(0, 10000)
        self.success_per_chat.setValue(self.current_settings.get('success_per_chat', 0))
        layout.addWidget(self.success_per_chat, 1, 1)

        # 3) Максимум успешных приглашений с одного аккаунта
        layout.addWidget(QLabel("Максимум успешных приглашений с аккаунта:"), 2, 0)
        self.success_per_account = QSpinBox()
        self.success_per_account.setRange(0, 10000)
        self.success_per_account.setValue(self.current_settings.get('success_per_account', 0))
        layout.addWidget(self.success_per_account, 2, 1)

        # 4) Задержка после старта (в секундах)
        layout.addWidget(QLabel("Задержка после старта, сек:"), 3, 0)
        self.delay_after_start = QSpinBox()
        self.delay_after_start.setRange(0, 3600)
        self.delay_after_start.setValue(self.current_settings.get('delay_after_start', 0))
        layout.addWidget(self.delay_after_start, 3, 1)

        # 5) Задержка между приглашениями (в секундах)
        layout.addWidget(QLabel("Задержка между приглашениями, сек:"), 4, 0)
        self.delay_between = QSpinBox()
        self.delay_between.setRange(0, 3600)
        self.delay_between.setValue(self.current_settings.get('delay_between', 0))
        layout.addWidget(self.delay_between, 4, 1)

        return group


    def _create_account_security_group(self) -> QGroupBox:
        group = QGroupBox("Параметры безопасности аккаунта")
        layout = QGridLayout(group)
        layout.setSpacing(10)

        # 1) Ошибок «спамблока» подряд – до исключения аккаунта
        layout.addWidget(QLabel("Максимум ошибок спамблока на аккаунт:"), 0, 0)
        self.acc_spam_limit = QSpinBox()
        self.acc_spam_limit.setRange(0, 100)
        self.acc_spam_limit.setValue(self.current_settings.get('acc_spam_limit', 3))
        layout.addWidget(self.acc_spam_limit, 0, 1)

        # 2) Количество списаний денежных средств до исключения аккаунта
        layout.addWidget(QLabel("Максимум списаний на аккаунт:"), 1, 0)
        self.acc_writeoff_limit = QSpinBox()
        self.acc_writeoff_limit.setRange(0, 100)
        self.acc_writeoff_limit.setValue(self.current_settings.get('acc_writeoff_limit', 2))
        layout.addWidget(self.acc_writeoff_limit, 1, 1)

        # 3) Количество блокировок приглашений до исключения аккаунта
        layout.addWidget(QLabel("Максимум блокировок приглашений на аккаунт:"), 2, 0)
        self.acc_block_invite_limit = QSpinBox()
        self.acc_block_invite_limit.setRange(0, 100)
        self.acc_block_invite_limit.setValue(self.current_settings.get('acc_block_invite_limit', 5))
        layout.addWidget(self.acc_block_invite_limit, 2, 1)

        return group


    def _create_chat_security_group(self) -> QGroupBox:
        group = QGroupBox("Параметры безопасности чата")
        layout = QGridLayout(group)
        layout.setSpacing(10)

        # 1) Сколько аккаунтов подряд бросили «спамблок» – до отключения чата
        layout.addWidget(QLabel("Максимум аккаунтов со спамблоком подряд:"), 0, 0)
        self.chat_spam_accounts = QSpinBox()
        self.chat_spam_accounts.setRange(0, 100)
        self.chat_spam_accounts.setValue(self.current_settings.get('chat_spam_accounts', 3))
        layout.addWidget(self.chat_spam_accounts, 0, 1)

        # 2) Сколько аккаунтов подряд списали средства – до отключения чата
        layout.addWidget(QLabel("Максимум аккаунтов со списаниями подряд:"), 1, 0)
        self.chat_writeoff_accounts = QSpinBox()
        self.chat_writeoff_accounts.setRange(0, 100)
        self.chat_writeoff_accounts.setValue(self.current_settings.get('chat_writeoff_accounts', 2))
        layout.addWidget(self.chat_writeoff_accounts, 1, 1)

        # 3) Сколько аккаунтов подряд получили неизвестную ошибку – до отключения чата
        layout.addWidget(QLabel("Максимум аккаунтов с неизвестной ошибкой подряд:"), 2, 0)
        self.chat_unknown_error_accounts = QSpinBox()
        self.chat_unknown_error_accounts.setRange(0, 100)
        self.chat_unknown_error_accounts.setValue(self.current_settings.get('chat_unknown_error_accounts', 1))
        layout.addWidget(self.chat_unknown_error_accounts, 2, 1)

        # 4) Сколько аккаунтов подряд заморозили – до отключения чата
        layout.addWidget(QLabel("Максимум аккаунтов с заморозкой подряд:"), 3, 0)
        self.chat_freeze_accounts = QSpinBox()
        self.chat_freeze_accounts.setRange(0, 100)
        self.chat_freeze_accounts.setValue(self.current_settings.get('chat_freeze_accounts', 1))
        layout.addWidget(self.chat_freeze_accounts, 3, 1)

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
        """Центрируем диалог над top-level окном родителя, или по центру экрана."""
        # Если есть родитель, берём его top-level окно (чтобы geometry был валидным)
        parent = self.parent()
        if parent:
            parent = parent.window()
        # Вычисляем прямоугольник, над которым будем центрировать
        if isinstance(parent, QWidget):
            target_rect = parent.frameGeometry()
        else:
            target_rect = QApplication.primaryScreen().geometry()
        # Центр этого прямоугольника
        center_point = target_rect.center()
        # Сдвигаем левый-верхний угол диалога так, чтобы его центр совпал с центром target
        self.move(center_point.x() - self.width() // 2,
                  center_point.y() - self.height() // 2)

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
            
            QGroupBox {
                background: rgba(40, 40, 40, 0.9);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 8px;
                margin-top: 16px;
                padding: 12px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 8px;
                color: #FFFFFF;
                background: rgba(20, 20, 20, 0.95);
                font-weight: 600;
            }
            
            
            QGroupBox#SettingsGroup {
                background: rgba(30, 30, 30, 0.8);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 8px;
                padding: 16px;
                margin-top: 20px;
                font-size: 15px;
                font-weight: 600;
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
        return {
            # главные
            'threads_per_chat': self.threads_per_chat.value(),
            'success_per_chat': self.success_per_chat.value(),
            'success_per_account': self.success_per_account.value(),
            'delay_after_start': self.delay_after_start.value(),
            'delay_between': self.delay_between.value(),

            # безопасность аккаунтов
            'acc_spam_limit': self.acc_spam_limit.value(),
            'acc_writeoff_limit': self.acc_writeoff_limit.value(),
            'acc_block_invite_limit': self.acc_block_invite_limit.value(),

            # безопасность чата
            'chat_spam_accounts': self.chat_spam_accounts.value(),
            'chat_writeoff_accounts': self.chat_writeoff_accounts.value(),
            'chat_unknown_error_accounts': self.chat_unknown_error_accounts.value(),
            'chat_freeze_accounts': self.chat_freeze_accounts.value(),
        }


class CreateProfileDialog(QDialog):
    """Диалог создания нового профиля инвайтера"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Создать профиль инвайтера")
        self.setModal(True)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(400, 200)
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)

        container = QFrame()
        container.setObjectName("DialogContainer")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        label = QLabel("Введите название профиля:")
        label.setStyleSheet("font-size:16px; color:#FFF; font-weight:bold;")
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Название профиля")
        self.name_input.setFixedHeight(30)

        buttons = QHBoxLayout()
        buttons.addStretch()
        cancel = QPushButton("Отменить")
        cancel.setFixedSize(100, 32)
        cancel.clicked.connect(self.reject)
        create = QPushButton("Создать")
        create.setFixedSize(100, 32)
        create.clicked.connect(self.accept)
        buttons.addWidget(cancel)
        buttons.addWidget(create)

        layout.addWidget(label)
        layout.addWidget(self.name_input)
        layout.addLayout(buttons)
        main_layout.addWidget(container)

        container.setStyleSheet(
            "QFrame#DialogContainer { background: rgba(20,20,20,0.95); border-radius:8px; }"
        )

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

        return group

    def _create_security_settings_group(self) -> QGroupBox:
        """Создает группу настроек безопасности"""
        group = QGroupBox("Настройки безопасности")
        group.setObjectName("SettingsGroup")
        layout = QGridLayout(group)
        layout.setSpacing(10)

        # Ошибок спамблока до остановки
        layout.addWidget(QLabel("Спамблоков до остановки:"), 0, 0)
        self.spam_errors = QSpinBox()
        self.spam_errors.setObjectName("SettingsSpinBox")
        self.spam_errors.setRange(1, 50)
        self.spam_errors.setValue(3)
        layout.addWidget(self.spam_errors, 0, 1)

        # Списаний до остановки
        layout.addWidget(QLabel("Списаний до остановки:"), 1, 0)
        self.writeoff_limit = QSpinBox()
        self.writeoff_limit.setObjectName("SettingsSpinBox")
        self.writeoff_limit.setRange(1, 20)
        self.writeoff_limit.setValue(2)
        layout.addWidget(self.writeoff_limit, 1, 1)

        return group

    def showEvent(self, event):
        super().showEvent(event)
        self._center_on_parent()

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
        """Центрируем диалог над top-level окном родителя, или по центру экрана."""
        # Если есть родитель, берём его top-level окно (чтобы geometry был валидным)
        parent = self.parent()
        if parent:
            parent = parent.window()
        # Вычисляем прямоугольник, над которым будем центрировать
        if isinstance(parent, QWidget):
            target_rect = parent.frameGeometry()
        else:
            target_rect = QApplication.primaryScreen().geometry()
        # Центр этого прямоугольника
        center_point = target_rect.center()
        # Сдвигаем левый-верхний угол диалога так, чтобы его центр совпал с центром target
        self.move(center_point.x() - self.width() // 2,
                  center_point.y() - self.height() // 2)

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
        name = self.name_input.text().strip() or "Новый профиль"
        return {
            'name': name,
            'invite_type': 'Классический',
            'threads_per_chat': 2,
            'chat_limit': 50,
            'account_limit': 100,
            'invite_delay': 30,
            'spam_errors': 3,
            'writeoff_limit': 2,
            'is_running': False,
            'users_list': [],
            'chats_list': [],
            'extended_settings': {}
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


def show_extended_settings_dialog(parent, current_settings: Dict = None) -> Dict:
    """Показывает диалог расширенных настроек"""
    dialog = ExtendedSettingsDialog(parent, current_settings)
    if dialog.exec() == QDialog.Accepted:
        return dialog.get_settings()
    return None  # Возвращаем None если отменили


def show_main_admins_setup_dialog(parent, profile_name: str) -> Dict[str, any]:
    """
    НОВАЯ ФУНКЦИЯ: Показывает полный диалог настройки админ-логики
    Объединяет выбор главных админов и ввод токена бота

    Args:
        parent: Родительский виджет
        profile_name: Имя профиля

    Returns:
        Dict: Результат настройки с главными админами и токеном
    """
    try:
        result = {
            'main_admins': [],
            'bot_token': '',
            'success': False
        }

        # Шаг 1: Выбор главных админов
        logger.info(f"👑 Настройка главных админов для профиля: {profile_name}")

        selected_admins = show_main_admins_dialog(parent, profile_name)

        if not selected_admins:
            logger.info("❌ Выбор главных админов отменен")
            return result

        result['main_admins'] = selected_admins

        # Шаг 2: Ввод токена бота
        logger.info(f"🤖 Настройка токена бота для профиля: {profile_name}")

        current_token = load_bot_token_from_profile(profile_name)
        bot_token = show_bot_token_dialog(parent, profile_name, current_token)

        if not bot_token:
            logger.info("❌ Ввод токена бота отменен")
            return result

        result['bot_token'] = bot_token
        result['success'] = True

        logger.info(f"✅ Админ-логика настроена для {profile_name}: {len(selected_admins)} админов, токен настроен")

        return result

    except Exception as e:
        logger.error(f"❌ Ошибка настройки админ-логики: {e}")
        return {'main_admins': [], 'bot_token': '', 'success': False}


def validate_admin_inviter_setup(profile_name: str) -> Dict[str, any]:
    """
    НОВАЯ ФУНКЦИЯ: Валидирует готовность профиля для админ-инвайтера

    Args:
        profile_name: Имя профиля

    Returns:
        Dict: Результат валидации
    """
    try:
        from paths import get_main_admins_list, load_bot_token, validate_profile_structure

        # Базовая валидация структуры
        validation = validate_profile_structure(profile_name)

        if validation['errors']:
            return {
                'ready': False,
                'errors': validation['errors'],
                'message': 'Ошибки в структуре профиля'
            }

        # Проверяем главных админов
        main_admins = get_main_admins_list(profile_name)
        if not main_admins:
            return {
                'ready': False,
                'errors': ['Не назначены главные админы'],
                'message': 'Назначьте хотя бы одного главного админа'
            }

        # Проверяем токен бота
        bot_token = load_bot_token(profile_name)
        if not bot_token:
            return {
                'ready': False,
                'errors': ['Не настроен токен бота'],
                'message': 'Настройте токен бота для управления правами'
            }

        # Все проверки пройдены
        return {
            'ready': True,
            'errors': [],
            'warnings': validation['warnings'],
            'info': validation['info'],
            'message': f'Профиль готов: {len(main_admins)} админов, токен настроен',
            'main_admins_count': len(main_admins),
            'has_bot_token': True
        }

    except Exception as e:
        logger.error(f"❌ Ошибка валидации профиля {profile_name}: {e}")
        return {
            'ready': False,
            'errors': [f'Ошибка валидации: {e}'],
            'message': 'Ошибка при проверке профиля'
        }


# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ для интеграции

def get_profile_admin_info(profile_name: str) -> Dict[str, any]:
    """
    НОВАЯ ФУНКЦИЯ: Получает информацию об админ-настройках профиля

    Args:
        profile_name: Имя профиля

    Returns:
        Dict: Информация об админах и боте
    """
    try:
        from paths import get_main_admins_list, load_bot_token

        main_admins = get_main_admins_list(profile_name)
        bot_token = load_bot_token(profile_name)

        return {
            'profile_name': profile_name,
            'main_admins': main_admins,
            'main_admins_count': len(main_admins),
            'has_bot_token': bool(bot_token),
            'bot_token_length': len(bot_token) if bot_token else 0,
            'ready_for_admin_invite': len(main_admins) > 0 and bool(bot_token)
        }

    except Exception as e:
        logger.error(f"❌ Ошибка получения информации об админах: {e}")
        return {
            'profile_name': profile_name,
            'main_admins': [],
            'main_admins_count': 0,
            'has_bot_token': False,
            'bot_token_length': 0,
            'ready_for_admin_invite': False,
            'error': str(e)
        }