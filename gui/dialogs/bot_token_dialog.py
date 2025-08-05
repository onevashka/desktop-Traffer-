from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QLineEdit, QFrame, QSpacerItem, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer
from loguru import logger
from pathlib import Path
from typing import List


class BotTokensDialog(QDialog):
    """НОВЫЙ: Диалог управления токенами ботов - как диалог базы пользователей"""

    def __init__(self, parent=None, profile_name: str = ""):
        super().__init__(parent)
        self.profile_name = profile_name
        self.current_tokens = []

        self.setWindowTitle(f"Токены ботов - {profile_name}")
        self.setModal(True)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(1000, 800)

        # Загружаем существующие токены
        self._load_current_tokens()
        self._init_ui()

        QTimer.singleShot(0, self._center_on_parent)

    def _center_on_parent(self):
        """Центрирует диалог относительно родителя"""
        if self.parent():
            parent_geo = self.parent().geometry()
            x = parent_geo.x() + (parent_geo.width() - self.width()) // 2
            y = parent_geo.y() + (parent_geo.height() - self.height()) // 2
            self.move(x, y)

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
        """Создает интерфейс диалога"""
        # Основной layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(20)

        # Контейнер для контента
        self.content_container = QFrame()
        self.content_container.setObjectName("DialogContainer")
        content_layout = QVBoxLayout(self.content_container)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(20)

        # Заголовок с иконкой
        self._create_header(content_layout)

        # Инструкция
        self._create_instructions(content_layout)

        # Текстовое поле для токенов
        self._create_tokens_input(content_layout)

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

        title_label = QLabel(f"Токены ботов для профиля: {self.profile_name}")
        title_label.setObjectName("DialogTitle")

        desc_label = QLabel(
            f"Управление токенами Telegram ботов. Текущий файл: {self.profile_name}/bot_tokens.txt\n"
            f"Найдено токенов: {len(self.current_tokens)}"
        )
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

        layout.addWidget(instructions_widget)

    def _create_tokens_input(self, layout):
        """Создает поле ввода токенов"""
        # Заголовок поля
        tokens_label = QLabel("Токены ботов (по одному на строку):")
        tokens_label.setObjectName("StepLabel")
        layout.addWidget(tokens_label)

        # Поле ввода
        self.tokens_text = QTextEdit()
        self.tokens_text.setObjectName("TokensTextEdit")
        self.tokens_text.setPlaceholderText(
            "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz\n5678901234:DEFghiJKLmnoPQRstuvWXYZ\n...")
        self.tokens_text.setPlainText('\n'.join(self.current_tokens))
        self.tokens_text.textChanged.connect(self._on_tokens_changed)

        layout.addWidget(self.tokens_text)

        # Статус
        self.status_label = QLabel(f"Токенов в поле: {len(self.current_tokens)}")
        self.status_label.setObjectName("DialogDescription")
        layout.addWidget(self.status_label)

    def _create_buttons(self, layout):
        """Создает кнопки диалога"""
        layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding))

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

        layout.addLayout(buttons_layout)

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
            }

            QLabel#StepLabel {
                font-size: 14px;
                font-weight: 600;
                color: rgba(255, 255, 255, 0.9);
                margin: 8px 0 4px 0;
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
                background: #111827;
                border: 1px solid #374151;
                border-radius: 8px;
                color: #FFFFFF;
                font-size: 13px;
                font-family: 'Consolas', 'Monaco', monospace;
                padding: 12px;
                min-height: 200px;
            }

            QTextEdit#TokensTextEdit:focus {
                border-color: #2563EB;
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
