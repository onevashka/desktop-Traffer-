# gui/dialogs/bot_token_dialog.py - ИСПРАВЛЕННАЯ ВЕРСИЯ С ЦЕНТРИРОВАНИЕМ

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QLineEdit, QFrame, QSpacerItem, QSizePolicy, QApplication, QWidget
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QScreen
from loguru import logger
from pathlib import Path
from typing import List, Optional


class BotTokenDialog(QDialog):
    """Диалог ввода токена бота"""

    def __init__(self, parent=None, profile_name: str = "", current_token: str = ""):
        super().__init__(parent)
        self.profile_name = profile_name
        self.current_token = current_token
        self.bot_token = ""

        self.setWindowTitle(f"Токен бота - {profile_name}")
        self.setModal(True)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(600, 400)

        self._init_ui()
        # ИСПРАВЛЕНО: Центрируем как в базе пользователей
        QTimer.singleShot(0, self._center_on_parent)

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

    def _init_ui(self):
        """Создает интерфейс диалога"""
        # Основной layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # Контейнер для контента
        self.content_container = QFrame()
        self.content_container.setObjectName("DialogContainer")
        content_layout = QVBoxLayout(self.content_container)
        content_layout.setContentsMargins(30, 30, 30, 30)
        content_layout.setSpacing(20)

        # Заголовок с иконкой
        self._create_header(content_layout)

        # Инструкция
        self._create_instructions(content_layout)

        # Поле ввода токена
        self._create_token_input(content_layout)

        # Кнопки
        self._create_buttons(content_layout)

        main_layout.addWidget(self.content_container)
        self._apply_styles()

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

        desc_label = QLabel("Укажите токен Telegram бота для управления правами")
        desc_label.setObjectName("DialogDescription")
        desc_label.setWordWrap(True)

        text_layout.addWidget(title_label)
        text_layout.addWidget(desc_label)

        header_layout.addWidget(icon_label)
        header_layout.addLayout(text_layout, 1)

        layout.addLayout(header_layout)

    def _create_instructions(self, layout):
        """Создает инструкцию"""
        instructions_text = """
🔧 Как получить токен бота:

1. Найдите @BotFather в Telegram
2. Отправьте команду /newbot
3. Придумайте имя и username для бота
4. Скопируйте токен и вставьте ниже

💡 Токен выглядит как: 1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
        """.strip()

        instructions_widget = QTextEdit()
        instructions_widget.setPlainText(instructions_text)
        instructions_widget.setReadOnly(True)
        instructions_widget.setMaximumHeight(120)
        instructions_widget.setObjectName("InstructionsText")

        layout.addWidget(instructions_widget)

    def _create_token_input(self, layout):
        """Создает поле ввода токена"""
        # Заголовок поля
        token_label = QLabel("Токен бота:")
        token_label.setObjectName("StepLabel")
        layout.addWidget(token_label)

        # Поле ввода
        self.token_input = QLineEdit()
        self.token_input.setObjectName("TokenInput")
        self.token_input.setPlaceholderText("1234567890:ABCdefGHIjklMNOpqrsTUVwxyz")
        self.token_input.setText(self.current_token)
        self.token_input.textChanged.connect(self._on_token_changed)

        layout.addWidget(self.token_input)

        # Статус
        self.status_label = QLabel("Введите токен бота")
        self.status_label.setObjectName("DialogDescription")
        layout.addWidget(self.status_label)

    def _create_buttons(self, layout):
        """Создает кнопки диалога"""
        layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding))

        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(12)

        # Кнопка очистки
        clear_btn = QPushButton("Очистить")
        clear_btn.setObjectName("ClearButton")
        clear_btn.clicked.connect(self._clear_token)

        # Кнопка отмены
        cancel_btn = QPushButton("Отменить")
        cancel_btn.setObjectName("CancelButton")
        cancel_btn.clicked.connect(self.reject)

        # Кнопка сохранения
        self.save_btn = QPushButton("Сохранить токен")
        self.save_btn.setObjectName("SaveButton")
        self.save_btn.clicked.connect(self._save_token)

        buttons_layout.addWidget(clear_btn)
        buttons_layout.addStretch()
        buttons_layout.addWidget(cancel_btn)
        buttons_layout.addWidget(self.save_btn)

        layout.addLayout(buttons_layout)

    def _on_token_changed(self):
        """Обработчик изменения токена"""
        token = self.token_input.text().strip()

        if not token:
            self.status_label.setText("Введите токен бота")
        elif self._is_valid_token(token):
            self.status_label.setText("✅ Токен корректный")
        else:
            self.status_label.setText("❌ Неправильный формат токена")

    def _is_valid_token(self, token: str) -> bool:
        """Проверяет валидность токена"""
        if not token:
            return False

        # Базовая проверка формата: числа:буквы
        parts = token.split(':')
        return len(parts) == 2 and parts[0].isdigit() and len(parts[1]) > 10

    def _clear_token(self):
        """Очищает поле токена"""
        self.token_input.clear()

    def _save_token(self):
        """Сохраняет токен"""
        token = self.token_input.text().strip()

        if not token:
            from gui.notifications import show_warning
            show_warning(
                "Пустой токен",
                "Введите токен бота"
            )
            return

        if not self._is_valid_token(token):
            from gui.notifications import show_warning
            show_warning(
                "Неверный токен",
                "Проверьте правильность токена бота"
            )
            return

        self.bot_token = token
        self.accept()

    def _apply_styles(self):
        """Применяет стили"""
        self.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1E1E2E, stop:1 #161622);
            }

            QFrame#DialogContainer {
                background: rgba(30, 30, 46, 0.95);
                border-radius: 16px;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }

            QLabel#DialogIcon {
                font-size: 32px;
                background: rgba(245, 158, 11, 0.1);
                border-radius: 24px;
                border: 2px solid rgba(245, 158, 11, 0.2);
            }

            QLabel#DialogTitle {
                font-size: 20px;
                font-weight: 600;
                color: #FFFFFF;
                margin-bottom: 8px;
            }

            QLabel#DialogDescription {
                font-size: 14px;
                color: rgba(255, 255, 255, 0.7);
                line-height: 1.4;
            }

            QLabel#StepLabel {
                font-size: 14px;
                font-weight: 600;
                color: rgba(255, 255, 255, 0.9);
                margin: 8px 0 4px 0;
            }

            QTextEdit#InstructionsText {
                background: rgba(17, 24, 39, 0.6);
                border: 1px solid rgba(245, 158, 11, 0.2);
                border-radius: 8px;
                color: rgba(255, 255, 255, 0.8);
                font-size: 13px;
                padding: 12px;
            }

            QLineEdit#TokenInput {
                background: #111827;
                border: 1px solid #374151;
                border-radius: 8px;
                color: #FFFFFF;
                font-size: 13px;
                font-family: 'Consolas', 'Monaco', monospace;
                padding: 12px;
            }

            QLineEdit#TokenInput:focus {
                border-color: #F59E0B;
            }

            QPushButton#ClearButton {
                background: rgba(239, 68, 68, 0.2);
                border: 1px solid rgba(239, 68, 68, 0.5);
                border-radius: 8px;
                color: #EF4444;
                font-size: 14px;
                font-weight: 600;
                padding: 12px 24px;
            }

            QPushButton#ClearButton:hover {
                background: rgba(239, 68, 68, 0.3);
                border-color: #EF4444;
            }

            QPushButton#CancelButton {
                background: rgba(156, 163, 175, 0.2);
                border: 1px solid rgba(156, 163, 175, 0.5);
                border-radius: 8px;
                color: rgba(255, 255, 255, 0.8);
                font-size: 14px;
                font-weight: 600;
                padding: 12px 24px;
            }

            QPushButton#CancelButton:hover {
                background: rgba(156, 163, 175, 0.3);
                color: #FFFFFF;
            }

            QPushButton#SaveButton {
                background: #F59E0B;
                border: 1px solid #F59E0B;
                border-radius: 8px;
                color: #FFFFFF;
                font-size: 14px;
                font-weight: 600;
                padding: 12px 24px;
            }

            QPushButton#SaveButton:hover {
                background: #D97706;
                border-color: #D97706;
            }
        """)

    def get_token(self) -> str:
        """Возвращает введенный токен"""
        return self.bot_token


class BotTokensDialog(QDialog):
    """НОВЫЙ: Диалог управления токенами ботов - в стиле диалога базы пользователей"""

    def __init__(self, parent=None, profile_name: str = ""):
        super().__init__(parent)
        self.profile_name = profile_name
        self.current_tokens = []

        self.setWindowTitle(f"Токены ботов - {profile_name}")
        self.setModal(True)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(1400, 1200)  # Размер как у базы пользователей

        # Загружаем существующие токены
        self._load_current_tokens()
        self._init_ui()

        # ИСПРАВЛЕНО: Центрируем как в базе пользователей
        QTimer.singleShot(0, self._center_on_parent)

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

    def _load_current_tokens(self):
        """Загружает текущие токены из файла"""
        try:
            from paths import get_profile_folder
            profile_folder = get_profile_folder(self.profile_name)
            tokens_file = profile_folder / "bot_tokens.txt"

            if tokens_file.exists():
                content = tokens_file.read_text(encoding='utf-8')
                self.current_tokens = [line.strip() for line in content.split('\n') if line.strip()]
                logger.info(f"📖 Загружено токенов: {len(self.current_tokens)}")
            else:
                self.current_tokens = []
                logger.info("📄 Файл токенов не найден, создаем новый")

        except Exception as e:
            logger.error(f"❌ Ошибка загрузки токенов: {e}")
            self.current_tokens = []

    def _init_ui(self):
        """Создает интерфейс диалога - полностью в стиле базы пользователей"""
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
        icon_label = QLabel("🤖")
        icon_label.setObjectName("DialogIcon")
        icon_label.setFixedSize(48, 48)
        icon_label.setAlignment(Qt.AlignCenter)

        # Заголовок
        title_label = QLabel(f"Токены ботов - {self.profile_name}")
        title_label.setObjectName("DialogTitle")
        title_label.setWordWrap(True)

        header_layout.addWidget(icon_label)
        header_layout.addWidget(title_label, 1)

        # Описание
        desc = QLabel(
            f"Управление токенами Telegram ботов для профиля.\n"
            f"Файл: {self.profile_name}/bot_tokens.txt | Найдено токенов: {len(self.current_tokens)}"
        )
        desc.setObjectName("DialogDescription")
        desc.setWordWrap(True)

        # Инструкция
        instructions_text = """
🔧 Как получить токены ботов:

1. Найдите @BotFather в Telegram
2. Отправьте команду /newbot для каждого бота
3. Придумайте имена и username для ботов
4. Скопируйте токены и вставьте ниже (по одному на строку)

💡 Токен выглядит как: 1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
        """.strip()

        instructions_widget = QTextEdit()
        instructions_widget.setPlainText(instructions_text)
        instructions_widget.setReadOnly(True)
        instructions_widget.setMaximumHeight(140)
        instructions_widget.setObjectName("InstructionsText")

        # Текстовое поле для токенов
        self.tokens_text = QTextEdit()
        self.tokens_text.setObjectName("TokensTextEdit")
        self.tokens_text.setPlaceholderText(
            "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz\n"
            "5678901234:DEFghiJKLmnoPQRstuvWXYZ\n"
            "9012345678:GHIjklMNOpqrsTUVwxyzABC\n"
            "..."
        )
        self.tokens_text.setPlainText('\n'.join(self.current_tokens))
        self.tokens_text.textChanged.connect(self._on_tokens_changed)

        # Информация
        self.info_label = QLabel(f"💡 Токенов в поле: {len(self.current_tokens)}")
        self.info_label.setObjectName("InfoLabel")

        # Статус валидации
        self.status_label = QLabel(f"Токенов в поле: {len(self.current_tokens)}")
        self.status_label.setObjectName("DialogDescription")

        # Кнопки
        buttons_layout = self._create_buttons()

        # Добавляем все элементы
        content_layout.addLayout(header_layout)
        content_layout.addWidget(desc)
        content_layout.addWidget(instructions_widget)
        content_layout.addWidget(QLabel("Токены ботов (по одному на строку):"))
        content_layout.addWidget(self.tokens_text)
        content_layout.addWidget(self.info_label)
        content_layout.addWidget(self.status_label)
        content_layout.addLayout(buttons_layout)

        main_layout.addWidget(self.content_container)
        self._apply_styles()

    def _create_buttons(self):
        """Создает кнопки диалога"""
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(12)

        # Кнопка очистки
        clear_btn = QPushButton("Очистить все")
        clear_btn.setObjectName("ClearButton")
        clear_btn.clicked.connect(self._clear_tokens)

        # Кнопка отмены
        cancel_btn = QPushButton("Отменить")
        cancel_btn.setObjectName("CancelButton")
        cancel_btn.clicked.connect(self.reject)

        # Кнопка сохранения
        self.save_btn = QPushButton("Сохранить токены")
        self.save_btn.setObjectName("SaveButton")
        self.save_btn.clicked.connect(self._save_tokens)

        buttons_layout.addWidget(clear_btn)
        buttons_layout.addStretch()
        buttons_layout.addWidget(cancel_btn)
        buttons_layout.addWidget(self.save_btn)

        return buttons_layout

    def _on_tokens_changed(self):
        """Обработчик изменения текста токенов"""
        text = self.tokens_text.toPlainText()
        tokens = [line.strip() for line in text.split('\n') if line.strip()]
        valid_tokens = [token for token in tokens if self._is_valid_token(token)]

        self.status_label.setText(
            f"Токенов в поле: {len(tokens)} | Валидных: {len(valid_tokens)}"
        )

    def _is_valid_token(self, token: str) -> bool:
        """Проверяет валидность токена"""
        if not token:
            return False

        # Базовая проверка формата: числа:буквы
        parts = token.split(':')
        return len(parts) == 2 and parts[0].isdigit() and len(parts[1]) > 10

    def _clear_tokens(self):
        """Очищает поле токенов"""
        self.tokens_text.clear()

    def _save_tokens(self):
        """Сохраняет токены в файл"""
        try:
            text = self.tokens_text.toPlainText()
            tokens = [line.strip() for line in text.split('\n') if line.strip()]

            # Валидация
            valid_tokens = []
            invalid_count = 0

            for token in tokens:
                if self._is_valid_token(token):
                    valid_tokens.append(token)
                else:
                    invalid_count += 1

            if not valid_tokens:
                from gui.notifications import show_warning
                show_warning(
                    "Нет валидных токенов",
                    "Введите хотя бы один корректный токен бота"
                )
                return

            # Сохраняем в файл
            from paths import get_profile_folder
            profile_folder = get_profile_folder(self.profile_name)
            profile_folder.mkdir(parents=True, exist_ok=True)

            tokens_file = profile_folder / "bot_tokens.txt"
            tokens_file.write_text('\n'.join(valid_tokens), encoding='utf-8')

            logger.info(f"💾 Сохранено токенов: {len(valid_tokens)}")

            # Уведомление
            from gui.notifications import show_success
            message = f"🤖 Сохранено {len(valid_tokens)} токенов ботов"
            if invalid_count > 0:
                message += f"\n⚠️ Пропущено некорректных: {invalid_count}"

            show_success("Токены сохранены", message)
            self.accept()

        except Exception as e:
            logger.error(f"❌ Ошибка сохранения токенов: {e}")
            from gui.notifications import show_error
            show_error("Ошибка сохранения", f"Не удалось сохранить токены: {e}")

    def _apply_styles(self):
        """Применяет стили в стиле диалога базы пользователей"""
        self.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1E1E2E, stop:1 #161622);
            }

            QFrame#DialogContainer {
                background: rgba(30, 30, 46, 0.95);
                border-radius: 16px;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }

            QLabel#DialogIcon {
                font-size: 32px;
                background: rgba(59, 130, 246, 0.1);
                border-radius: 24px;
                border: 2px solid rgba(59, 130, 246, 0.2);
            }

            QLabel#DialogTitle {
                font-size: 20px;
                font-weight: 600;
                color: #FFFFFF;
                margin-bottom: 8px;
            }

            QLabel#DialogDescription {
                font-size: 14px;
                color: rgba(255, 255, 255, 0.7);
                line-height: 1.4;
                margin-bottom: 16px;
            }

            QLabel#InfoLabel {
                font-size: 13px;
                color: rgba(255, 255, 255, 0.6);
                margin: 8px 0;
            }

            QTextEdit#InstructionsText {
                background: rgba(17, 24, 39, 0.6);
                border: 1px solid rgba(59, 130, 246, 0.2);
                border-radius: 8px;
                color: rgba(255, 255, 255, 0.8);
                font-size: 13px;
                padding: 12px;
            }

            QTextEdit#TokensTextEdit {
                background: rgba(17, 24, 39, 0.6);
                border: 1px solid rgba(59, 130, 246, 0.2);
                border-radius: 8px;
                color: #FFFFFF;
                font-size: 13px;
                font-family: 'Consolas', 'Monaco', monospace;
                padding: 12px;
                min-height: 300px;
            }

            QTextEdit#TokensTextEdit:focus {
                border-color: #2563EB;
                background: rgba(17, 24, 39, 0.8);
            }

            QPushButton#ClearButton {
                background: rgba(239, 68, 68, 0.2);
                border: 1px solid rgba(239, 68, 68, 0.5);
                border-radius: 8px;
                color: #EF4444;
                font-size: 14px;
                font-weight: 600;
                padding: 12px 24px;
            }

            QPushButton#ClearButton:hover {
                background: rgba(239, 68, 68, 0.3);
                border-color: #EF4444;
            }

            QPushButton#CancelButton {
                background: rgba(156, 163, 175, 0.2);
                border: 1px solid rgba(156, 163, 175, 0.5);
                border-radius: 8px;
                color: rgba(255, 255, 255, 0.8);
                font-size: 14px;
                font-weight: 600;
                padding: 12px 24px;
            }

            QPushButton#CancelButton:hover {
                background: rgba(156, 163, 175, 0.3);
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
        """)

    def get_tokens(self) -> List[str]:
        """Возвращает список токенов"""
        text = self.tokens_text.toPlainText()
        tokens = [line.strip() for line in text.split('\n') if line.strip()]
        return [token for token in tokens if self._is_valid_token(token)]


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


def show_bot_tokens_dialog(parent, profile_name: str) -> List[str]:
    """
    НОВАЯ ФУНКЦИЯ: Показывает диалог управления токенами ботов

    Args:
        parent: Родительский виджет
        profile_name: Имя профиля

    Returns:
        List[str]: Список сохраненных токенов или пустой список если отменено
    """
    dialog = BotTokensDialog(parent, profile_name)

    if dialog.exec() == QDialog.Accepted:
        return dialog.get_tokens()

    return []


def load_bot_token_from_profile(profile_name: str) -> str:
    """
    Загружает токен бота из файла профиля

    Args:
        profile_name: Имя профиля

    Returns:
        str: Токен бота или пустая строка если не найден
    """
    try:
        from paths import get_profile_folder
        profile_folder = get_profile_folder(profile_name)

        # Пробуем загрузить из config.json
        config_file = profile_folder / "config.json"
        if config_file.exists():
            import json
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                bot_account = config.get('bot_account', {})
                if isinstance(bot_account, dict):
                    return bot_account.get('token', '')

        # Пробуем загрузить из bot_token.txt (legacy)
        token_file = profile_folder / "bot_token.txt"
        if token_file.exists():
            token = token_file.read_text(encoding='utf-8').strip()
            return token

        return ""

    except Exception as e:
        logger.error(f"❌ Ошибка загрузки токена для {profile_name}: {e}")
        return ""