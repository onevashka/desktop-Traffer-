"""
Красивое модальное окно для архивации аккаунтов
"""

import shutil
import subprocess
from pathlib import Path
from typing import List, Dict, Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QWidget, QFrame, QGraphicsOpacityEffect,
    QGraphicsDropShadowEffect, QApplication, QComboBox, QLineEdit
)
from PySide6.QtCore import (
    Qt, QPropertyAnimation, QEasingCurve, QTimer, QRect,
    QParallelAnimationGroup, QThread, Signal
)
from PySide6.QtGui import QFont, QColor, QPalette, QPixmap, QPainter
from loguru import logger


class ArchiveWorker(QThread):
    """Воркер для архивации в отдельном потоке"""
    progress = Signal(str)  # Сообщение о прогрессе
    finished = Signal(bool, str)  # Успех, сообщение

    def __init__(self, accounts_info, archive_name, archive_format, archive_path):
        super().__init__()
        self.accounts_info = accounts_info
        self.archive_name = archive_name
        self.archive_format = archive_format
        self.archive_path = Path(archive_path)

    def run(self):
        """Выполняет архивацию"""
        try:
            self.progress.emit("Создание временной папки...")

            # Создаем временную папку для архивации
            temp_folder = self.archive_path / self.archive_name
            temp_folder.mkdir(parents=True, exist_ok=True)

            # Копируем файлы аккаунтов
            copied_count = 0
            for account in self.accounts_info:
                self.progress.emit(f"Копирование {account['name']}...")

                # Копируем .session файл
                session_src = Path(account['session_file'])
                json_src = Path(account['json_file'])

                if session_src.exists():
                    shutil.copy2(session_src, temp_folder / session_src.name)
                if json_src.exists():
                    shutil.copy2(json_src, temp_folder / json_src.name)

                copied_count += 1

            self.progress.emit(f"Скопировано {copied_count} аккаунтов")

            # Архивируем папку
            self.progress.emit("Создание архива...")
            archive_file = self.archive_path / f"{self.archive_name}.{self.archive_format}"

            if self.archive_format == "zip":
                self._create_zip_archive(temp_folder, archive_file)
            else:  # rar
                self._create_rar_archive(temp_folder, archive_file)

            # Удаляем временную папку
            self.progress.emit("Очистка временных файлов...")
            shutil.rmtree(temp_folder)

            self.finished.emit(True, f"Архив создан: {archive_file}")

        except Exception as e:
            logger.error(f"Ошибка архивации: {e}")
            self.finished.emit(False, f"Ошибка архивации: {str(e)}")

    def _create_zip_archive(self, source_folder, archive_file):
        """Создает ZIP архив"""
        shutil.make_archive(str(archive_file.with_suffix('')), 'zip', source_folder)

    def _create_rar_archive(self, source_folder, archive_file):
        """Создает RAR архив"""
        # Пытаемся найти WinRAR
        winrar_paths = [
            r"C:\Program Files\WinRAR\WinRAR.exe",
            r"C:\Program Files (x86)\WinRAR\WinRAR.exe"
        ]

        winrar_exe = None
        for path in winrar_paths:
            if Path(path).exists():
                winrar_exe = path
                break

        if not winrar_exe:
            raise Exception("WinRAR не найден")

        # Команда для создания RAR архива
        cmd = [
            winrar_exe,
            "a",  # Добавить в архив
            "-r",  # Рекурсивно
            str(archive_file),
            str(source_folder / "*")
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"Ошибка создания RAR: {result.stderr}")


class ArchiveAccountsDialog(QDialog):
    """Красивое модальное окно для архивации аккаунтов"""

    ACCEPTED = 1
    REJECTED = 0

    def __init__(self, accounts_info: List[Dict], current_category: str, parent=None):
        super().__init__(parent)

        self.accounts_info = accounts_info
        self.current_category = current_category
        self.result_value = self.REJECTED
        self.archive_name = ""
        self.archive_format = "zip"
        self.archive_worker = None

        # Настройки окна
        self.setWindowTitle("Архивация аккаунтов")
        self.setModal(True)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # Размеры
        self.setFixedSize(650, 600)

        # Создаем UI
        self._create_ui()
        self._setup_animations()
        self._center_on_parent()

        # Применяем стили
        self._apply_styles()

        # Показываем с анимацией
        self._animate_in()

    def _create_ui(self):
        """Создает интерфейс диалога"""
        # Основной контейнер
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Контейнер для контента
        self.content_container = QFrame()
        self.content_container.setObjectName("ContentContainer")
        content_layout = QVBoxLayout(self.content_container)
        content_layout.setContentsMargins(30, 30, 30, 30)
        content_layout.setSpacing(20)

        # Заголовок с иконкой
        header_layout = QHBoxLayout()
        header_layout.setSpacing(15)

        # Иконка
        icon_label = QLabel("📦")
        icon_label.setObjectName("DialogIcon")
        icon_label.setFixedSize(48, 48)
        icon_label.setAlignment(Qt.AlignCenter)

        # Заголовок
        title_label = QLabel("Архивация аккаунтов")
        title_label.setObjectName("DialogTitle")
        title_label.setWordWrap(True)

        header_layout.addWidget(icon_label)
        header_layout.addWidget(title_label, 1)

        # Основное сообщение
        count = len(self.accounts_info)
        if count == 1:
            message = "Создать архив с выбранным аккаунтом:"
        else:
            message = f"Создать архив с {count} аккаунт(ами):"

        message_label = QLabel(message)
        message_label.setObjectName("DialogMessage")
        message_label.setWordWrap(True)

        # Настройки архивации
        settings_layout = self._create_archive_settings()

        # Список аккаунтов
        accounts_container = self._create_accounts_list()

        # Информация
        info_label = QLabel("ℹ️ Архив будет создан в папке 'Архивы' в корне приложения")
        info_label.setObjectName("InfoLabel")
        info_label.setWordWrap(True)

        # Кнопки
        buttons_layout = self._create_buttons()

        # Сборка layout
        content_layout.addLayout(header_layout)
        content_layout.addWidget(message_label)
        content_layout.addLayout(settings_layout)
        content_layout.addWidget(accounts_container, 1)
        content_layout.addWidget(info_label)
        content_layout.addLayout(buttons_layout)

        main_layout.addWidget(self.content_container)

        # Тень
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(30)
        shadow.setXOffset(0)
        shadow.setYOffset(10)
        shadow.setColor(QColor(0, 0, 0, 120))
        self.content_container.setGraphicsEffect(shadow)

    def _create_archive_settings(self) -> QVBoxLayout:
        """Создает настройки архивации"""
        layout = QVBoxLayout()
        layout.setSpacing(15)

        # Название архива
        name_layout = QVBoxLayout()
        name_layout.setSpacing(8)

        name_label = QLabel("Название архива:")
        name_label.setObjectName("SettingsLabel")

        self.name_input = QLineEdit()
        self.name_input.setObjectName("ArchiveNameInput")
        self.name_input.setPlaceholderText("Введите название архива...")
        self.name_input.setFixedHeight(40)

        # Автоматическое название по умолчанию
        from datetime import datetime
        default_name = f"accounts_{self.current_category}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.name_input.setText(default_name)

        name_layout.addWidget(name_label)
        name_layout.addWidget(self.name_input)

        # Формат архива
        format_layout = QVBoxLayout()
        format_layout.setSpacing(8)

        format_label = QLabel("Формат архива:")
        format_label.setObjectName("SettingsLabel")

        self.format_combo = QComboBox()
        self.format_combo.setObjectName("FormatCombo")
        self.format_combo.setFixedHeight(40)

        # Проверяем доступность WinRAR
        if self._check_winrar_available():
            self.format_combo.addItem("📦 ZIP архив", "zip")
            self.format_combo.addItem("📦 RAR архив", "rar")
        else:
            self.format_combo.addItem("📦 ZIP архив", "zip")
            self.format_combo.addItem("📦 RAR архив (недоступен)", "zip")

        format_layout.addWidget(format_label)
        format_layout.addWidget(self.format_combo)

        layout.addLayout(name_layout)
        layout.addLayout(format_layout)

        return layout

    def _check_winrar_available(self) -> bool:
        """Проверяет доступность WinRAR через менеджер аккаунтов"""
        try:
            from src.accounts.manager import check_winrar_available
            return check_winrar_available()
        except Exception as e:
            logger.error(f"Ошибка проверки WinRAR: {e}")
            return False

    def _create_accounts_list(self) -> QWidget:
        """Создает список аккаунтов"""
        container = QFrame()
        container.setObjectName("AccountsContainer")

        # Подпись
        list_label = QLabel(f"Аккаунты для архивации ({len(self.accounts_info)}):")
        list_label.setObjectName("ListLabel")

        # Скроллируемая область
        scroll_area = QScrollArea()
        scroll_area.setObjectName("AccountsScroll")
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # Виджет для списка
        accounts_widget = QWidget()
        accounts_layout = QVBoxLayout(accounts_widget)
        accounts_layout.setContentsMargins(10, 10, 10, 10)
        accounts_layout.setSpacing(8)

        # Добавляем аккаунты
        for i, account in enumerate(self.accounts_info):
            account_item = self._create_account_item(account, i)
            accounts_layout.addWidget(account_item)

        # Если аккаунтов много, показываем только первые 12
        if len(self.accounts_info) > 12:
            accounts_layout.addWidget(self._create_more_indicator())

        accounts_layout.addStretch()
        scroll_area.setWidget(accounts_widget)

        # Layout контейнера
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(8)
        container_layout.addWidget(list_label)
        container_layout.addWidget(scroll_area)

        return container

    def _create_account_item(self, account: Dict, index: int) -> QWidget:
        """Создает элемент списка аккаунтов"""
        if index >= 12:  # Показываем только первые 12
            return QWidget()

        item = QFrame()
        item.setObjectName("AccountItem")

        layout = QHBoxLayout(item)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(10)

        # Иконка архивации
        icon = QLabel("📦")
        icon.setObjectName("AccountIcon")
        icon.setFixedSize(20, 20)

        # Информация об аккаунте
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)

        # Имя аккаунта
        name_label = QLabel(account['name'])
        name_label.setObjectName("AccountName")

        # Дополнительная информация
        details = []
        if account.get('full_name') and account['full_name'] != '?':
            details.append(account['full_name'])
        if account.get('phone') and account['phone'] != '?':
            details.append(account['phone'])

        if details:
            details_label = QLabel(" • ".join(details))
            details_label.setObjectName("AccountDetails")
            info_layout.addWidget(details_label)

        info_layout.addWidget(name_label)

        # Размер файлов
        size_label = self._get_files_size(account)
        size_label.setObjectName("AccountSize")

        layout.addWidget(icon)
        layout.addLayout(info_layout, 1)
        layout.addWidget(size_label)

        return item

    def _get_files_size(self, account: Dict) -> QLabel:
        """Получает размер файлов аккаунта"""
        try:
            session_size = Path(account['session_file']).stat().st_size if Path(account['session_file']).exists() else 0
            json_size = Path(account['json_file']).stat().st_size if Path(account['json_file']).exists() else 0
            total_size = session_size + json_size

            if total_size < 1024:
                size_text = f"{total_size} B"
            elif total_size < 1024 * 1024:
                size_text = f"{total_size / 1024:.1f} KB"
            else:
                size_text = f"{total_size / (1024 * 1024):.1f} MB"

            return QLabel(size_text)
        except:
            return QLabel("? KB")

    def _create_more_indicator(self) -> QWidget:
        """Создает индикатор "еще N аккаунтов"""
        remaining = len(self.accounts_info) - 12

        indicator = QLabel(f"... и еще {remaining} аккаунт(ов)")
        indicator.setObjectName("MoreIndicator")
        indicator.setAlignment(Qt.AlignCenter)
        indicator.setStyleSheet("""
            QLabel#MoreIndicator {
                color: rgba(255, 255, 255, 0.6);
                font-style: italic;
                font-size: 12px;
                padding: 8px;
            }
        """)

        return indicator

    def _create_buttons(self) -> QHBoxLayout:
        """Создает кнопки диалога"""
        layout = QHBoxLayout()
        layout.setSpacing(12)

        # Кнопка отмены
        self.cancel_button = QPushButton("Отменить")
        self.cancel_button.setObjectName("CancelButton")
        self.cancel_button.setFixedSize(120, 44)
        self.cancel_button.clicked.connect(self._on_cancel)

        # Кнопка подтверждения
        self.confirm_button = QPushButton("Создать архив")
        self.confirm_button.setObjectName("ConfirmButton")
        self.confirm_button.setFixedSize(140, 44)
        self.confirm_button.clicked.connect(self._on_confirm)

        layout.addStretch()
        layout.addWidget(self.cancel_button)
        layout.addWidget(self.confirm_button)

        return layout

    def _apply_styles(self):
        """Применяет стили к диалогу"""
        self.setStyleSheet("""
            /* Основной контейнер */
            QFrame#ContentContainer {
                background: rgba(20, 20, 20, 0.95);
                border: 2px solid rgba(255, 255, 255, 0.1);
                border-radius: 16px;
                backdrop-filter: blur(20px);
            }

            /* Иконка диалога */
            QLabel#DialogIcon {
                font-size: 32px;
                background: rgba(59, 130, 246, 0.1);
                border-radius: 24px;
                border: 2px solid rgba(59, 130, 246, 0.3);
            }

            /* Заголовок */
            QLabel#DialogTitle {
                font-size: 20px;
                font-weight: 700;
                color: #FFFFFF;
                margin: 0;
            }

            /* Сообщение */
            QLabel#DialogMessage {
                font-size: 14px;
                color: rgba(255, 255, 255, 0.8);
                line-height: 1.4;
                margin: 0;
            }

            /* Подписи настроек */
            QLabel#SettingsLabel {
                font-size: 14px;
                font-weight: 500;
                color: rgba(255, 255, 255, 0.9);
                margin: 0;
            }

            /* Поле ввода названия */
            QLineEdit#ArchiveNameInput {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 14px;
                color: rgba(255, 255, 255, 0.9);
                selection-background-color: rgba(59, 130, 246, 0.3);
            }

            QLineEdit#ArchiveNameInput:focus {
                border-color: #3B82F6;
                background: rgba(255, 255, 255, 0.08);
            }

            /* Выпадающий список формата */
            QComboBox#FormatCombo {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 14px;
                color: rgba(255, 255, 255, 0.9);
                selection-background-color: rgba(59, 130, 246, 0.3);
            }

            QComboBox#FormatCombo:hover {
                border-color: rgba(59, 130, 246, 0.5);
                background: rgba(255, 255, 255, 0.08);
            }

            QComboBox#FormatCombo::drop-down {
                border: none;
                padding-right: 8px;
            }

            QComboBox#FormatCombo QAbstractItemView {
                background: rgba(30, 30, 30, 0.95);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                selection-background-color: rgba(59, 130, 246, 0.3);
                color: rgba(255, 255, 255, 0.9);
                padding: 4px;
            }

            /* Остальные стили аналогично другим диалогам... */
            
            /* Кнопка отмены */
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

            /* Кнопка подтверждения */
            QPushButton#ConfirmButton {
                background: #059669;
                border: 1px solid #059669;
                border-radius: 8px;
                color: #FFFFFF;
                font-size: 14px;
                font-weight: 600;
            }

            QPushButton#ConfirmButton:hover {
                background: #047857;
                border-color: #047857;
            }

            /* Контейнер аккаунтов */
            QFrame#AccountsContainer {
                background: rgba(255, 255, 255, 0.02);
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 8px;
                padding: 8px;
            }

            /* Элемент аккаунта */
            QFrame#AccountItem {
                background: rgba(255, 255, 255, 0.03);
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 6px;
                margin: 0;
            }

            QFrame#AccountItem:hover {
                background: rgba(255, 255, 255, 0.05);
                border-color: rgba(59, 130, 246, 0.3);
            }
        """)

    def _setup_animations(self):
        """Настраивает анимации"""
        # Эффект прозрачности
        self.opacity_effect = QGraphicsOpacityEffect()
        self.opacity_effect.setOpacity(0.0)
        self.setGraphicsEffect(self.opacity_effect)

        # Анимация прозрачности
        self.opacity_animation = QPropertyAnimation(self.opacity_effect, b"opacity")

        # Анимация масштабирования
        self.scale_animation = QPropertyAnimation(self, b"geometry")

        # Группа анимаций
        self.animation_group = QParallelAnimationGroup()
        self.animation_group.addAnimation(self.opacity_animation)
        self.animation_group.addAnimation(self.scale_animation)

    def _center_on_parent(self):
        """Центрирует диалог относительно родителя"""
        if self.parent():
            parent_rect = self.parent().geometry()
            x = parent_rect.x() + (parent_rect.width() - self.width()) // 2
            y = parent_rect.y() + (parent_rect.height() - self.height()) // 2
            self.move(x, y)
        else:
            # Центрируем на экране
            screen = QApplication.primaryScreen().geometry()
            x = (screen.width() - self.width()) // 2
            y = (screen.height() - self.height()) // 2
            self.move(x, y)

    def _animate_in(self):
        """Анимация появления"""
        # Получаем финальную позицию
        final_rect = self.geometry()

        # Начальная позиция (меньше и выше)
        start_rect = QRect(
            final_rect.x() + 30,
            final_rect.y() - 30,
            final_rect.width() - 60,
            final_rect.height() - 60
        )

        self.setGeometry(start_rect)

        # Анимация прозрачности
        self.opacity_animation.setDuration(300)
        self.opacity_animation.setStartValue(0.0)
        self.opacity_animation.setEndValue(1.0)
        self.opacity_animation.setEasingCurve(QEasingCurve.OutCubic)

        # Анимация масштабирования
        self.scale_animation.setDuration(300)
        self.scale_animation.setStartValue(start_rect)
        self.scale_animation.setEndValue(final_rect)
        self.scale_animation.setEasingCurve(QEasingCurve.OutBack)

        # Запускаем анимацию
        self.animation_group.start()

    def _animate_out(self, callback=None):
        """Анимация исчезновения"""
        current_rect = self.geometry()

        # Конечная позиция (меньше и выше)
        end_rect = QRect(
            current_rect.x() + 30,
            current_rect.y() - 30,
            current_rect.width() - 60,
            current_rect.height() - 60
        )

        # Анимация прозрачности
        self.opacity_animation.setDuration(200)
        self.opacity_animation.setStartValue(1.0)
        self.opacity_animation.setEndValue(0.0)
        self.opacity_animation.setEasingCurve(QEasingCurve.InCubic)

        # Анимация масштабирования
        self.scale_animation.setDuration(200)
        self.scale_animation.setStartValue(current_rect)
        self.scale_animation.setEndValue(end_rect)
        self.scale_animation.setEasingCurve(QEasingCurve.InBack)

        # Подключаем callback
        if callback:
            self.animation_group.finished.connect(callback)

        # Запускаем анимацию
        self.animation_group.start()

    def _on_cancel(self):
        """Обработка отмены"""
        self.result_value = self.REJECTED
        self._animate_out(self.close)

    def _on_confirm(self):
        """Обработка подтверждения"""
        # Получаем данные
        self.archive_name = self.name_input.text().strip()
        if not self.archive_name:
            # Показываем ошибку
            self.name_input.setStyleSheet("""
                QLineEdit#ArchiveNameInput {
                    border: 2px solid #EF4444;
                    background: rgba(239, 68, 68, 0.1);
                }
            """)
            return

        self.archive_format = self.format_combo.currentData()
        self.result_value = self.ACCEPTED
        self._animate_out(self.close)

    def exec(self) -> int:
        """Показывает диалог модально"""
        super().exec()
        return self.result_value

    def get_archive_settings(self) -> Dict:
        """Возвращает настройки архивации"""
        return {
            'name': self.archive_name,
            'format': self.archive_format
        }


def show_archive_accounts_dialog(parent, accounts_info: List[Dict], current_category: str) -> Optional[Dict]:
    """
    Удобная функция для показа диалога архивации аккаунтов

    Returns:
        Словарь с настройками архивации или None если отменили
    """
    dialog = ArchiveAccountsDialog(accounts_info, current_category, parent)
    result = dialog.exec()

    if result == ArchiveAccountsDialog.ACCEPTED:
        return dialog.get_archive_settings()
    else:
        return None