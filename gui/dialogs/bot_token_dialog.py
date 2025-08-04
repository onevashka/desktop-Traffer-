# gui/dialogs/bot_token_dialog.py
"""
Диалог ввода токена бота для профиля инвайтера
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTextEdit, QFrame, QSpacerItem, QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from loguru import logger
from pathlib import Path


class BotTokenDialog(QDialog):
    """Диалог ввода токена бота"""

    def __init__(self, parent, profile_name: str, current_token: str = ""):
        super().__init__(parent)
        self.profile_name = profile_name
        self.current_token = current_token
        self.token = ""

        self.setWindowTitle("Настройка токена бота")
        self.setFixedSize(600, 400)
        self.setModal(True)

        # Стили
        self._setup_styles()

        # UI
        self._create_ui()

        # Загружаем текущий токен если есть
        if current_token:
            self.token_input.setText(current_token)

    def _setup_styles(self):
        """Настройка стилей диалога"""
        self.setStyleSheet("""
            QDialog {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 rgba(15, 23, 42, 0.98),
                    stop: 1 rgba(30, 41, 59, 0.95)
                );
                border: 2px solid rgba(255, 255, 255, 0.1);
                border-radius: 16px;
            }

            QLabel#DialogIcon {
                font-size: 32px;
                background: rgba(34, 197, 94, 0.1);
                border-radius: 24px;
                border: 2px solid rgba(34, 197, 94, 0.3);
            }

            QLabel#DialogTitle {
                font-size: 20px;
                font-weight: 700;
                color: #FFFFFF;
                margin: 0;
            }

            QLabel#DialogDescription {
                font-size: 14px;
                color: rgba(255, 255, 255, 0.7);
                margin-top: 5px;
                line-height: 1.4;
            }

            QLabel#StepLabel {
                font-size: 13px;
                color: rgba(255, 255, 255, 0.8);
                font-weight: 500;
                margin: 8px 0 4px 0;
            }

            QLineEdit {
                background: rgba(255, 255, 255, 0.08);
                border: 2px solid rgba(255, 255, 255, 0.15);
                border-radius: 8px;
                padding: 12px 16px;
                color: #FFFFFF;
                font-size: 14px;
                font-family: 'Cascadia Code', 'Consolas', monospace;
            }

            QLineEdit:focus {
                border-color: rgba(34, 197, 94, 0.6);
                background: rgba(255, 255, 255, 0.12);
            }

            QLineEdit::placeholder {
                color: rgba(255, 255, 255, 0.4);
            }

            QTextEdit {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                padding: 12px;
                color: rgba(255, 255, 255, 0.8);
                font-size: 13px;
                line-height: 1.5;
            }

            QPushButton#CancelButton {
                background: rgba(255, 255, 255, 0.06);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 8px;
                color: rgba(255, 255, 255, 0.9);
                font-size: 14px;
                font-weight: 500;
                padding: 12px 24px;
            }

            QPushButton#CancelButton:hover {
                background: rgba(255, 255, 255, 0.1);
                border-color: rgba(255, 255, 255, 0.3);
                color: #FFFFFF;
            }

            QPushButton#SaveButton {
                background: #22C55E;
                border: 1px solid #22C55E;
                border-radius: 8px;
                color: #FFFFFF;
                font-size: 14px;
                font-weight: 600;
                padding: 12px 24px;
            }

            QPushButton#SaveButton:hover {
                background: #16A34A;
                border-color: #16A34A;
            }

            QPushButton#SaveButton:disabled {
                background: rgba(34, 197, 94, 0.3);
                border-color: rgba(34, 197, 94, 0.3);
                color: rgba(255, 255, 255, 0.5);
            }
        """)

    def _create_ui(self):
        """Создает UI диалога"""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(24, 24, 24, 24)

        # Заголовок
        self._create_header(layout)

        # Инструкция
        self._create_instructions(layout)

        # Поле ввода токена
        self._create_token_input(layout)

        # Кнопки
        self._create_buttons(layout)

    def _create_header(self, layout):
        """Создает заголовок диалога"""
        header_layout = QHBoxLayout()
        header_layout.setSpacing(15)

        # Иконка
        icon_label = QLabel("🤖")
        icon_label.setObjectName("DialogIcon")
        icon_label.setFixedSize(48, 48)
        icon_label.setAlignment(Qt.AlignCenter)

        # Заголовок и описание
        text_layout = QVBoxLayout()

        title_label = QLabel(f"Токен бота для профиля: {self.profile_name}")
        title_label.setObjectName("DialogTitle")

        desc_label = QLabel(
            "Введите токен Telegram бота для управления админ-правами в чатах.\n"
            "Токен будет сохранен в папке профиля."
        )
        desc_label.setObjectName("DialogDescription")
        desc_label.setWordWrap(True)

        text_layout.addWidget(title_label)
        text_layout.addWidget(desc_label)

        header_layout.addWidget(icon_label)
        header_layout.addLayout(text_layout, 1)

        layout.addLayout(header_layout)

    def _create_instructions(self, layout):
        """Создает инструкцию по получению токена"""
        instructions_text = """
🔧 Как получить токен бота:

1. Найдите @BotFather в Telegram
2. Отправьте команду /newbot
3. Придумайте имя для бота (например: "MyInviterBot")
4. Придумайте username для бота (должен заканчиваться на "_bot")
5. Скопируйте полученный токен и вставьте ниже

Токен выглядит как: 1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
        """.strip()

        instructions_widget = QTextEdit()
        instructions_widget.setPlainText(instructions_text)
        instructions_widget.setReadOnly(True)
        instructions_widget.setMaximumHeight(160)

        layout.addWidget(instructions_widget)

    def _create_token_input(self, layout):
        """Создает поле ввода токена"""
        # Заголовок поля
        token_label = QLabel("Токен бота:")
        token_label.setObjectName("StepLabel")
        layout.addWidget(token_label)

        # Поле ввода
        self.token_input = QLineEdit()
        self.token_input.setPlaceholderText("1234567890:ABCdefGHIjklMNOpqrsTUVwxyz")
        self.token_input.textChanged.connect(self._validate_token)
        layout.addWidget(self.token_input)

        # Статус валидации
        self.validation_label = QLabel("")
        self.validation_label.setObjectName("DialogDescription")
        layout.addWidget(self.validation_label)

    def _create_buttons(self, layout):
        """Создает кнопки диалога"""
        layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding))

        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(12)

        # Кнопка отмены
        cancel_btn = QPushButton("Отменить")
        cancel_btn.setObjectName("CancelButton")
        cancel_btn.clicked.connect(self.reject)

        # Кнопка сохранения
        self.save_btn = QPushButton("Сохранить токен")
        self.save_btn.setObjectName("SaveButton")
        self.save_btn.clicked.connect(self._save_token)
        self.save_btn.setEnabled(False)  # Изначально неактивна

        buttons_layout.addStretch()
        buttons_layout.addWidget(cancel_btn)
        buttons_layout.addWidget(self.save_btn)

        layout.addLayout(buttons_layout)

    def _validate_token(self):
        """Валидирует введенный токен"""
        token = self.token_input.text().strip()

        if not token:
            self.validation_label.setText("")
            self.save_btn.setEnabled(False)
            return

        # Простая валидация формата токена
        if self._is_valid_token_format(token):
            self.validation_label.setText("✅ Формат токена корректный")
            self.validation_label.setStyleSheet("color: #22C55E;")
            self.save_btn.setEnabled(True)
        else:
            self.validation_label.setText("❌ Неверный формат токена")
            self.validation_label.setStyleSheet("color: #EF4444;")
            self.save_btn.setEnabled(False)

    def _is_valid_token_format(self, token: str) -> bool:
        """Проверяет формат токена бота"""
        # Базовая проверка формата: число:строка
        parts = token.split(':')
        if len(parts) != 2:
            return False

        bot_id, bot_hash = parts

        # ID бота должен быть числом
        if not bot_id.isdigit():
            return False

        # Хеш должен быть буквенно-цифровым и достаточно длинным
        if len(bot_hash) < 20 or not bot_hash.replace('_', '').replace('-', '').isalnum():
            return False

        return True

    def _save_token(self):
        """Сохраняет токен в файл профиля"""
        try:
            token = self.token_input.text().strip()

            if not token or not self._is_valid_token_format(token):
                from gui.notifications import show_error
                show_error(
                    "Ошибка валидации",
                    "Введите корректный токен бота"
                )
                return

            # Получаем путь к папке профиля
            profile_folder = self._get_profile_folder()
            if not profile_folder:
                from gui.notifications import show_error
                show_error(
                    "Ошибка",
                    f"Не найдена папка профиля: {self.profile_name}"
                )
                return

            # Сохраняем токен в файл
            token_file = profile_folder / "bot_token.txt"
            token_file.write_text(token, encoding='utf-8')

            self.token = token
            logger.info(f"💾 Токен бота сохранен для профиля: {self.profile_name}")

            from gui.notifications import show_success
            show_success(
                "Токен сохранен",
                f"🤖 Токен бота успешно сохранен в профиле {self.profile_name}"
            )

            self.accept()

        except Exception as e:
            logger.error(f"❌ Ошибка сохранения токена: {e}")
            from gui.notifications import show_error
            show_error(
                "Ошибка сохранения",
                f"Не удалось сохранить токен: {e}"
            )

    def _get_profile_folder(self) -> Path:
        """Получает путь к папке профиля"""
        try:
            from src.modules.impl.inviter.profile_manager import InviterProfileManager

            # Создаем временный менеджер профилей для получения пути
            profile_manager = InviterProfileManager()
            profiles = profile_manager.get_all_profiles()

            for profile in profiles:
                if profile.get('name') == self.profile_name:
                    return Path(profile['folder_path'])

            logger.error(f"❌ Профиль {self.profile_name} не найден")
            return None

        except Exception as e:
            logger.error(f"❌ Ошибка получения папки профиля: {e}")
            return None

    def get_token(self) -> str:
        """Возвращает введенный токен"""
        return self.token


def show_bot_token_dialog(parent, profile_name: str, current_token: str = "") -> str:
    """
    Показывает диалог ввода токена бота

    Args:
        parent: Родительский виджет
        profile_name: Имя профиля
        current_token: Текущий токен (если есть)

    Returns:
        str: Введенный токен или пустая строка если отменено
    """
    dialog = BotTokenDialog(parent, profile_name, current_token)

    if dialog.exec() == QDialog.Accepted:
        return dialog.get_token()

    return ""


def load_bot_token_from_profile(profile_name: str) -> str:
    """
    Загружает токен бота из файла профиля
    УСТАРЕЛА: Используйте load_bot_token() из paths.py

    Args:
        profile_name: Имя профиля

    Returns:
        str: Токен бота или пустая строка если не найден
    """
    try:
        # Перенаправляем на функцию из paths.py
        from paths import load_bot_token
        return load_bot_token(profile_name)

    except Exception as e:
        logger.error(f"❌ Ошибка загрузки токена: {e}")
        return ""