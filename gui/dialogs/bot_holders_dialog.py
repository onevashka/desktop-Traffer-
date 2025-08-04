# gui/dialogs/bot_holders_dialog.py
"""
Диалог выбора аккаунтов для создания ботов
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QWidget, QCheckBox, QTabWidget,
    QApplication, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QColor
from loguru import logger
from typing import List, Dict


class AccountListWidget(QWidget):
    """Виджет со списком аккаунтов"""

    def __init__(self, title: str, accounts: List[Dict], checkable: bool = False):
        super().__init__()
        self.accounts = accounts
        self.checkable = checkable
        self.checked_accounts = []
        self.account_items = []

        self.init_ui(title)

    def init_ui(self, title: str):
        """Инициализация UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # Заголовок
        title_label = QLabel(title)
        title_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: 600;
                color: #FFFFFF;
                padding: 10px 0;
            }
        """)
        layout.addWidget(title_label)

        # Информация о количестве
        self.info_label = QLabel()
        self.info_label.setStyleSheet("""
            QLabel {
                font-size: 13px;
                color: rgba(255, 255, 255, 0.7);
                padding-bottom: 10px;
            }
        """)
        layout.addWidget(self.info_label)

        # Скролл область
        scroll = QScrollArea()
        scroll.setObjectName("AccountsScroll")
        scroll.setWidgetResizable(True)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea#AccountsScroll {
                background: transparent;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
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

        # Контейнер для аккаунтов
        accounts_container = QWidget()
        accounts_layout = QVBoxLayout(accounts_container)
        accounts_layout.setContentsMargins(10, 10, 10, 10)
        accounts_layout.setSpacing(8)

        # Создаем элементы аккаунтов
        for account in self.accounts:
            account_item = self._create_account_item(account)
            accounts_layout.addWidget(account_item)
            self.account_items.append(account_item)

        accounts_layout.addStretch()
        scroll.setWidget(accounts_container)
        layout.addWidget(scroll)

        # Обновляем информацию
        self._update_info()

    def _create_account_item(self, account: Dict) -> QWidget:
        """Создает элемент аккаунта"""
        item = QFrame()
        item.setObjectName("AccountItem")
        item.setStyleSheet("""
            QFrame#AccountItem {
                background: rgba(255, 255, 255, 0.03);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
                padding: 12px;
                margin: 2px 0;
            }
            QFrame#AccountItem:hover {
                background: rgba(255, 255, 255, 0.06);
                border-color: rgba(59, 130, 246, 0.3);
            }
        """)

        layout = QHBoxLayout(item)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)

        # Чекбокс (если нужен)
        if self.checkable:
            checkbox = QCheckBox()
            checkbox.setObjectName("AccountCheckbox")
            checkbox.setStyleSheet("""
                QCheckBox::indicator {
                    width: 16px;
                    height: 16px;
                    border: 2px solid rgba(255, 255, 255, 0.3);
                    border-radius: 3px;
                    background: transparent;
                }
                QCheckBox::indicator:checked {
                    background: #3B82F6;
                    border-color: #3B82F6;
                    image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iOSIgdmlld0JveD0iMCAwIDEyIDkiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxwYXRoIGQ9Ik0xIDQuNUw0LjUgOEwxMSAxLjUiIHN0cm9rZT0id2hpdGUiIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIi8+Cjwvc3ZnPgo=);
                }
                QCheckBox::indicator:hover {
                    border-color: rgba(59, 130, 246, 0.6);
                }
            """)
            checkbox.toggled.connect(lambda checked, acc=account: self._on_account_toggled(acc, checked))
            layout.addWidget(checkbox)

        # Иконка статуса
        status_icon = "🤖" if account.get('has_bot') else "👤"
        icon_label = QLabel(status_icon)
        icon_label.setFixedSize(24, 24)
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                background: rgba(255, 255, 255, 0.08);
                border-radius: 12px;
            }
        """)
        layout.addWidget(icon_label)

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
            details_label = QLabel(" • ".join(details))
            details_label.setStyleSheet("""
                QLabel {
                    font-size: 12px;
                    color: rgba(255, 255, 255, 0.6);
                }
            """)
            info_layout.addWidget(details_label)

        layout.addLayout(info_layout)
        layout.addStretch()

        return item

    def _on_account_toggled(self, account: Dict, checked: bool):
        """Обработка изменения чекбокса"""
        if checked and account not in self.checked_accounts:
            self.checked_accounts.append(account)
        elif not checked and account in self.checked_accounts:
            self.checked_accounts.remove(account)

        self._update_info()

    def _update_info(self):
        """Обновляет информационную строку"""
        total = len(self.accounts)
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

        desc_label = QLabel(
            "Назначайте аккаунты держателями ботов для инвайтов через админку.\nВыбранные аккаунты будут перемещены в папку 'Держатели_ботов'")
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

        # Кнопка освободить от ботов
        self.release_btn = QPushButton("Освободить от ботов")
        self.release_btn.setObjectName("SecondaryButton")
        self.release_btn.setFixedSize(160, 44)
        self.release_btn.clicked.connect(self._release_bots)

        # Спейсер
        buttons_layout.addWidget(self.select_all_btn)
        buttons_layout.addWidget(self.release_btn)
        buttons_layout.addStretch()

        # Кнопка отмены
        cancel_btn = QPushButton("Отменить")
        cancel_btn.setObjectName("CancelButton")
        cancel_btn.setFixedSize(120, 44)
        cancel_btn.clicked.connect(self.reject)

        # Кнопка подтверждения (назначить ботов)
        self.confirm_btn = QPushButton("Назначить ботов")
        self.confirm_btn.setObjectName("ConfirmButton")
        self.confirm_btn.setFixedSize(140, 44)
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
                    checkable=True  # Делаем выбираемыми для возможности освобождения
                )
                self.tabs.addTab(holders_widget, f"🤖 Держатели ботов ({len(bot_holders)})")
                self.holders_widget = holders_widget
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
        """Выбирает все доступные аккаунты на текущей вкладке"""
        current_tab = self.tabs.currentWidget()

        if isinstance(current_tab, AccountListWidget) and current_tab.checkable:
            # Переключаем все чекбоксы на текущей вкладке
            for item in current_tab.account_items:
                checkbox = item.findChild(QCheckBox)
                if checkbox:
                    checkbox.setChecked(True)

    def _release_bots(self):
        """Освобождает выбранные аккаунты от ботов"""
        if not hasattr(self, 'holders_widget'):
            from gui.notifications import show_info
            show_info(
                "Освобождение ботов",
                "Нет держателей ботов для освобождения"
            )
            return

        selected_holders = self.holders_widget.get_selected_accounts()

        if not selected_holders:
            from gui.notifications import show_warning
            show_warning(
                "Освобождение ботов",
                "Выберите аккаунты для освобождения от ботов на вкладке 'Держатели ботов'"
            )
            return

        # Освобождаем выбранные аккаунты
        success_count = 0
        failed_accounts = []

        for account in selected_holders:
            account_name = account['name']
            success = self._release_bot_account(account_name)

            if success:
                success_count += 1
                logger.info(f"🔄 Аккаунт {account_name} освобожден от бота")
            else:
                failed_accounts.append(account_name)
                logger.error(f"❌ Не удалось освободить {account_name} от бота")

        # Обновляем AccountManager после перемещений
        if success_count > 0:
            self._update_account_manager()

        # Показываем результат
        if failed_accounts:
            from gui.notifications import show_error
            show_error(
                "Ошибки при освобождении",
                f"Освобождено: {success_count}, ошибок: {len(failed_accounts)}\n"
                f"Не удалось освободить: {', '.join(failed_accounts[:3])}" +
                (f" и еще {len(failed_accounts) - 3}" if len(failed_accounts) > 3 else "")
            )
        else:
            from gui.notifications import show_success
            show_success(
                "Аккаунты освобождены",
                f"🔄 Успешно освобождено {success_count} аккаунт(ов) от ботов\n"
                f"Аккаунты возвращены в папку 'Трафик'"
            )

        # Перезагружаем данные в диалоге
        self.tabs.clear()
        self.load_accounts()

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

            # Перемещаем выбранные аккаунты в папку Держатели_ботов
            success_count = 0
            failed_accounts = []

            for account in self.selected_accounts:
                account_name = account['name']
                success = self._assign_bot_account(account_name)

                if success:
                    success_count += 1
                    logger.info(f"✅ Аккаунт {account_name} назначен держателем бота")
                else:
                    failed_accounts.append(account_name)
                    logger.error(f"❌ Не удалось назначить {account_name} держателем бота")

            # Обновляем AccountManager после перемещений
            if success_count > 0:
                self._update_account_manager()

            # Показываем результат
            if failed_accounts:
                from gui.notifications import show_error
                show_error(
                    "Ошибки при назначении",
                    f"Назначено: {success_count}, ошибок: {len(failed_accounts)}\n"
                    f"Не удалось назначить: {', '.join(failed_accounts[:3])}" +
                    (f" и еще {len(failed_accounts) - 3}" if len(failed_accounts) > 3 else "")
                )
            else:
                from gui.notifications import show_success
                show_success(
                    "Аккаунты назначены",
                    f"🤖 Успешно назначено {success_count} аккаунт(ов) держателями ботов\n"
                    f"Аккаунты перемещены в папку 'Держатели_ботов'"
                )

            # Если хотя бы один аккаунт успешно назначен, отправляем сигнал
            if success_count > 0:
                # Обновляем данные после перемещения
                successful_accounts = [acc for acc in self.selected_accounts
                                       if acc['name'] not in failed_accounts]
                self.accounts_selected.emit(successful_accounts)
                self.accept()
            else:
                # Если ни один аккаунт не удалось назначить, не закрываем диалог
                return
        else:
            self.reject()

    def _release_bot_account(self, account_name: str) -> bool:
        """Освобождает аккаунт от бота через BotAccountManager"""
        try:
            from src.modules.impl.inviter.bot_account_manager import release_bot_account

            success, message = release_bot_account(account_name)

            if success:
                logger.info(f"🔄 {message}")
                return True
            else:
                logger.error(f"❌ {message}")
                return False

        except Exception as e:
            logger.error(f"❌ Ошибка освобождения бота для {account_name}: {e}")
            return False

    def _assign_bot_account(self, account_name: str) -> bool:
        """Назначает аккаунт держателем бота через BotAccountManager"""
        try:
            from src.modules.impl.inviter.bot_account_manager import assign_bot_account

            success, message = assign_bot_account(account_name)

            if success:
                logger.info(f"🤖 {message}")
                return True
            else:
                logger.error(f"❌ {message}")
                return False

        except Exception as e:
            logger.error(f"❌ Ошибка назначения бота для {account_name}: {e}")
            return False

    def _update_account_manager(self):
        """Обновляет AccountManager после изменений"""
        try:
            from src.accounts.manager import _account_manager
            import asyncio

            if _account_manager:
                # Запускаем обновление категории трафика в новом цикле событий
                def refresh_traffic():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        loop.run_until_complete(_account_manager.refresh_category("traffic"))
                    finally:
                        loop.close()

                # Запускаем обновление в отдельном потоке, чтобы не блокировать UI
                import threading
                refresh_thread = threading.Thread(target=refresh_traffic)
                refresh_thread.daemon = True
                refresh_thread.start()

                logger.info("📊 Запущено обновление AccountManager")
        except Exception as e:
            logger.error(f"❌ Ошибка обновления AccountManager: {e}")

    def _center_on_parent(self):
        """Центрирует диалог относительно родителя"""
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
        """Центрируем диалог при показе"""
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