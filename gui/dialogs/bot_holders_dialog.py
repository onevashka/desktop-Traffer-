# gui/dialogs/bot_holders_dialog.py
"""
Диалог выбора аккаунтов-держателей ботов для инвайта через админку
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QListWidget, QListWidgetItem, QFrame,
    QGraphicsDropShadowEffect, QSizePolicy, QWidget,
    QScrollArea, QCheckBox
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont
from typing import List, Dict, Optional
from loguru import logger
from pathlib import Path


class AccountListWidget(QWidget):
    """Виджет для отображения списка аккаунтов с чекбоксами"""

    def __init__(self, title: str, accounts: List[Dict], checkable: bool = True):
        super().__init__()
        self.checkable = checkable
        self.checked_accounts = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Заголовок
        header = QLabel(title)
        header.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: 600;
                color: rgba(255, 255, 255, 0.9);
                padding: 10px;
                background: rgba(255, 255, 255, 0.05);
                border-radius: 6px;
                margin-bottom: 10px;
            }
        """)
        layout.addWidget(header)

        # Скролл для списка
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
            }
            QScrollBar:vertical {
                background: rgba(255, 255, 255, 0.05);
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 0.2);
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(59, 130, 246, 0.6);
            }
        """)

        # Контейнер для аккаунтов
        self.accounts_container = QWidget()
        self.accounts_layout = QVBoxLayout(self.accounts_container)
        self.accounts_layout.setContentsMargins(10, 10, 10, 10)
        self.accounts_layout.setSpacing(5)

        # Добавляем аккаунты
        self.account_items = []
        for account in accounts:
            item = self._create_account_item(account)
            self.account_items.append(item)
            self.accounts_layout.addWidget(item)

        self.accounts_layout.addStretch()
        scroll.setWidget(self.accounts_container)
        layout.addWidget(scroll)

        # Информация о количестве
        self.info_label = QLabel(f"Всего: {len(accounts)} аккаунтов")
        self.info_label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                color: rgba(255, 255, 255, 0.6);
                padding: 5px;
            }
        """)
        layout.addWidget(self.info_label)

    def _create_account_item(self, account: Dict) -> QWidget:
        """Создает элемент аккаунта"""
        item = QWidget()
        item.setObjectName("AccountItem")
        item.setFixedHeight(60)

        layout = QHBoxLayout(item)
        layout.setContentsMargins(10, 5, 10, 5)

        # Чекбокс (если нужен)
        if self.checkable:
            checkbox = QCheckBox()
            checkbox.setStyleSheet("""
                QCheckBox::indicator {
                    width: 20px;
                    height: 20px;
                    border: 2px solid rgba(255, 255, 255, 0.4);
                    border-radius: 4px;
                    background: rgba(255, 255, 255, 0.05);
                }
                QCheckBox::indicator:checked {
                    background: #3B82F6;
                    border-color: #3B82F6;
                }
                QCheckBox::indicator:checked::after {
                    content: "";
                    width: 5px;
                    height: 10px;
                    border: solid white;
                    border-width: 0 2px 2px 0;
                    transform: rotate(45deg);
                    margin: 3px 0 0 6px;
                    display: block;
                }
            """)
            checkbox.toggled.connect(lambda checked: self._on_check_changed(account, checked))
            layout.addWidget(checkbox)

        # Информация об аккаунте
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)

        # Имя аккаунта
        name_label = QLabel(account.get('name', 'Unknown'))
        name_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: 600;
                color: #FFFFFF;
            }
        """)
        info_layout.addWidget(name_label)

        # Дополнительная информация
        details = []
        if account.get('phone'):
            details.append(f"📱 {account['phone']}")
        if account.get('full_name'):
            details.append(f"👤 {account['full_name']}")

        if details:
            details_label = QLabel(" | ".join(details))
            details_label.setStyleSheet("""
                QLabel {
                    font-size: 12px;
                    color: rgba(255, 255, 255, 0.6);
                }
            """)
            info_layout.addWidget(details_label)

        layout.addLayout(info_layout)
        layout.addStretch()

        # Статус (если есть бот)
        if account.get('has_bot'):
            bot_label = QLabel("🤖 Имеет бота")
            bot_label.setStyleSheet("""
                QLabel {
                    font-size: 12px;
                    color: #10B981;
                    font-weight: 500;
                    padding: 4px 8px;
                    background: rgba(16, 185, 129, 0.1);
                    border: 1px solid rgba(16, 185, 129, 0.3);
                    border-radius: 4px;
                }
            """)
            layout.addWidget(bot_label)

        # Стиль элемента
        item.setStyleSheet("""
            QWidget#AccountItem {
                background: rgba(255, 255, 255, 0.03);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 6px;
            }
            QWidget#AccountItem:hover {
                background: rgba(255, 255, 255, 0.05);
                border-color: rgba(59, 130, 246, 0.3);
            }
        """)

        # Сохраняем данные
        item.account_data = account

        return item

    def _on_check_changed(self, account: Dict, checked: bool):
        """Обработка изменения чекбокса"""
        if checked:
            if account not in self.checked_accounts:
                self.checked_accounts.append(account)
        else:
            if account in self.checked_accounts:
                self.checked_accounts.remove(account)

        # Обновляем информацию
        self._update_info()

    def _update_info(self):
        """Обновляет информацию о выборе"""
        total = len(self.account_items)
        selected = len(self.checked_accounts)

        if self.checkable and selected > 0:
            self.info_label.setText(f"Выбрано: {selected} из {total}")
        else:
            self.info_label.setText(f"Всего: {total} аккаунтов")

    def get_selected_accounts(self) -> List[Dict]:
        """Возвращает выбранные аккаунты"""
        return self.checked_accounts.copy()


class BotHoldersDialog(QDialog):
    """Диалог выбора аккаунтов для создания ботов"""

    accounts_selected = Signal(list)  # Сигнал с выбранными аккаунтами

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Выбор аккаунтов для ботов")
        self.setModal(True)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(900, 700)

        self.selected_accounts = []
        self.init_ui()
        self.load_accounts()

        # Центрируем после инициализации
        QTimer.singleShot(0, self._center_on_parent)

    def init_ui(self):
        """Инициализация интерфейса"""
        # Основной контейнер
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Контейнер для контента
        self.content_container = QFrame()
        self.content_container.setObjectName("DialogContainer")
        content_layout = QVBoxLayout(self.content_container)
        content_layout.setContentsMargins(30, 30, 30, 30)
        content_layout.setSpacing(20)

        # Заголовок
        self._create_header(content_layout)

        # Табы для разных списков
        self.tabs = QTabWidget()
        self.tabs.setObjectName("AccountTabs")
        self.tabs.setStyleSheet("""
            QTabWidget#AccountTabs::pane {
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                background: transparent;
                top: -1px;
            }

            QTabBar::tab {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-bottom: none;
                padding: 10px 20px;
                margin: 0 2px;
                border-radius: 8px 8px 0 0;
                color: rgba(255, 255, 255, 0.7);
                font-size: 13px;
                font-weight: 500;
            }

            QTabBar::tab:selected {
                background: rgba(59, 130, 246, 0.15);
                border: 1px solid rgba(59, 130, 246, 0.3);
                color: #FFFFFF;
                font-weight: 600;
            }

            QTabBar::tab:hover:!selected {
                background: rgba(255, 255, 255, 0.08);
                color: rgba(255, 255, 255, 0.9);
            }
        """)

        content_layout.addWidget(self.tabs)

        # Кнопки
        self._create_buttons(content_layout)

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

        title_label = QLabel("Выбор аккаунтов для создания ботов")
        title_label.setObjectName("DialogTitle")

        desc_label = QLabel("Выберите аккаунты, которые будут управлять ботами для инвайтов через админку")
        desc_label.setObjectName("DialogDescription")
        desc_label.setWordWrap(True)

        text_layout.addWidget(title_label)
        text_layout.addWidget(desc_label)

        header_layout.addWidget(icon_label)
        header_layout.addLayout(text_layout, 1)

        layout.addLayout(header_layout)

    def _create_buttons(self, layout):
        """Создает кнопки диалога"""
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(12)

        # Кнопка выбрать все
        self.select_all_btn = QPushButton("Выбрать все")
        self.select_all_btn.setObjectName("SecondaryButton")
        self.select_all_btn.setFixedSize(120, 44)
        self.select_all_btn.clicked.connect(self._select_all)

        # Спейсер
        buttons_layout.addWidget(self.select_all_btn)
        buttons_layout.addStretch()

        # Кнопка отмены
        cancel_btn = QPushButton("Отменить")
        cancel_btn.setObjectName("CancelButton")
        cancel_btn.setFixedSize(120, 44)
        cancel_btn.clicked.connect(self.reject)

        # Кнопка подтверждения
        self.confirm_btn = QPushButton("Подтвердить")
        self.confirm_btn.setObjectName("ConfirmButton")
        self.confirm_btn.setFixedSize(120, 44)
        self.confirm_btn.clicked.connect(self._confirm_selection)

        buttons_layout.addWidget(cancel_btn)
        buttons_layout.addWidget(self.confirm_btn)

        layout.addLayout(buttons_layout)

    def load_accounts(self):
        """Загружает списки аккаунтов"""
        try:
            # Загружаем доступные аккаунты из папки Аккаунты
            available_accounts = self._load_available_accounts()

            # Загружаем существующие аккаунты с ботами
            bot_holders = self._load_bot_holders()

            # Создаем вкладку с доступными аккаунтами
            if available_accounts:
                available_widget = AccountListWidget(
                    "Доступные аккаунты для назначения",
                    available_accounts,
                    checkable=True
                )
                self.tabs.addTab(available_widget, f"🟢 Доступные ({len(available_accounts)})")
                self.available_widget = available_widget

            # Создаем вкладку с держателями ботов
            if bot_holders:
                holders_widget = AccountListWidget(
                    "Аккаунты, которые уже имеют ботов",
                    bot_holders,
                    checkable=False
                )
                self.tabs.addTab(holders_widget, f"🤖 Держатели ботов ({len(bot_holders)})")

            # Если нет доступных аккаунтов
            if not available_accounts:
                empty_label = QLabel("Нет доступных аккаунтов для создания ботов")
                empty_label.setAlignment(Qt.AlignCenter)
                empty_label.setStyleSheet("""
                    QLabel {
                        font-size: 16px;
                        color: rgba(255, 255, 255, 0.5);
                        padding: 50px;
                    }
                """)
                self.tabs.addTab(empty_label, "🟢 Доступные (0)")

        except Exception as e:
            logger.error(f"❌ Ошибка загрузки аккаунтов: {e}")

    def _load_available_accounts(self) -> List[Dict]:
        """Загружает доступные аккаунты из папки трафика"""
        try:
            from src.accounts.manager import _account_manager

            if not _account_manager:
                logger.error("❌ AccountManager не инициализирован")
                return []

            # Получаем активные аккаунты из трафика
            available = []
            for name, account_data in _account_manager.traffic_accounts.items():
                if account_data.status == "active":
                    # Проверяем что аккаунт не в папке держателей ботов
                    if not self._is_bot_holder(name):
                        available.append({
                            'name': name,
                            'phone': account_data.info.get('phone', ''),
                            'full_name': account_data.info.get('full_name', ''),
                            'has_bot': False,
                            'account_data': account_data
                        })

            logger.info(f"📋 Загружено доступных аккаунтов: {len(available)}")
            return available

        except Exception as e:
            logger.error(f"❌ Ошибка загрузки доступных аккаунтов: {e}")
            return []

    def _load_bot_holders(self) -> List[Dict]:
        """Загружает аккаунты из папки Держатели_ботов"""
        try:
            from paths import BOT_HOLDERS_FOLDER

            if not BOT_HOLDERS_FOLDER.exists():
                BOT_HOLDERS_FOLDER.mkdir(parents=True, exist_ok=True)
                return []

            holders = []

            # Сканируем папку
            for session_file in BOT_HOLDERS_FOLDER.glob("*.session"):
                json_file = session_file.with_suffix(".json")

                if json_file.exists():
                    # Читаем информацию из JSON
                    import json
                    try:
                        with open(json_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)

                        holders.append({
                            'name': session_file.stem,
                            'phone': data.get('phone', ''),
                            'full_name': f"{data.get('first_name', '')} {data.get('last_name', '')}".strip(),
                            'has_bot': True
                        })
                    except Exception as e:
                        logger.error(f"❌ Ошибка чтения {json_file}: {e}")

            logger.info(f"🤖 Загружено держателей ботов: {len(holders)}")
            return holders

        except Exception as e:
            logger.error(f"❌ Ошибка загрузки держателей ботов: {e}")
            return []

    def _is_bot_holder(self, account_name: str) -> bool:
        """Проверяет является ли аккаунт держателем бота"""
        from paths import BOT_HOLDERS_FOLDER
        session_file = BOT_HOLDERS_FOLDER / f"{account_name}.session"
        return session_file.exists()

    def _select_all(self):
        """Выбирает все доступные аккаунты"""
        if hasattr(self, 'available_widget'):
            # Переключаем все чекбоксы
            for item in self.available_widget.account_items:
                checkbox = item.findChild(QCheckBox)
                if checkbox:
                    checkbox.setChecked(True)

    def _confirm_selection(self):
        """Подтверждает выбор аккаунтов"""
        if hasattr(self, 'available_widget'):
            self.selected_accounts = self.available_widget.get_selected_accounts()

            if not self.selected_accounts:
                # Показываем предупреждение
                from gui.notifications import show_warning
                show_warning(
                    "Выбор аккаунтов",
                    "Выберите хотя бы один аккаунт для создания бота"
                )
                return

            # Отправляем сигнал с выбранными аккаунтами
            self.accounts_selected.emit(self.selected_accounts)
            self.accept()
        else:
            self.reject()

    def _center_on_parent(self):
        """Центрирует диалог относительно родителя"""
        if self.parent():
            parent_rect = self.parent().frameGeometry()
            center_point = parent_rect.center()
            self.move(
                center_point.x() - self.width() // 2,
                center_point.y() - self.height() // 2
            )

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
                color: rgba(255, 255, 255, 0.7);
                margin-top: 5px;
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

            QPushButton#ConfirmButton {
                background: #3B82F6;
                border: 1px solid #3B82F6;
                border-radius: 8px;
                color: #FFFFFF;
                font-size: 14px;
                font-weight: 600;
            }

            QPushButton#ConfirmButton:hover {
                background: #2563EB;
                border-color: #2563EB;
            }

            QPushButton#SecondaryButton {
                background: rgba(59, 130, 246, 0.2);
                border: 1px solid rgba(59, 130, 246, 0.5);
                border-radius: 8px;
                color: #FFFFFF;
                font-size: 14px;
                font-weight: 500;
            }

            QPushButton#SecondaryButton:hover {
                background: rgba(59, 130, 246, 0.3);
                border-color: rgba(59, 130, 246, 0.7);
            }
        """)


def show_bot_holders_dialog(parent) -> List[Dict]:
    """
    Показывает диалог выбора аккаунтов для ботов

    Returns:
        List[Dict]: Список выбранных аккаунтов или пустой список
    """
    dialog = BotHoldersDialog(parent)

    selected = []

    def on_accounts_selected(accounts):
        nonlocal selected
        selected = accounts

    dialog.accounts_selected.connect(on_accounts_selected)

    if dialog.exec() == QDialog.Accepted:
        return selected

    return []