# gui/dialogs/main_admins_dialog.py - ИСПРАВЛЕННАЯ ВЕРСИЯ
"""
Диалог выбора главных админов для профиля инвайтера
Заменяет bot_holders_dialog.py с новой логикой
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QCheckBox, QScrollArea, QWidget, QFrame,
    QSizePolicy, QSpacerItem
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from loguru import logger
from pathlib import Path
from typing import List, Dict, Optional


class AccountListWidget(QWidget):
    """Виджет списка аккаунтов с чекбоксами"""

    def __init__(self, title: str, accounts: List[Dict], checkable: bool = True):
        super().__init__()
        self.accounts = accounts
        self.checkable = checkable
        self.account_items = []

        self._create_ui(title)

    def _create_ui(self, title: str):
        """Создает UI списка"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Заголовок
        title_label = QLabel(title)
        title_label.setObjectName("SectionTitle")
        title_label.setStyleSheet("""
            QLabel#SectionTitle {
                font-size: 16px;
                font-weight: 600;
                color: rgba(255, 255, 255, 0.9);
                margin-bottom: 8px;
            }
        """)
        layout.addWidget(title_label)

        # Скролл область
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollBar:vertical {
                background: rgba(255, 255, 255, 0.1);
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 0.3);
                border-radius: 4px;
            }
        """)

        # Контейнер для аккаунтов
        accounts_widget = QWidget()
        accounts_layout = QVBoxLayout(accounts_widget)
        accounts_layout.setSpacing(8)
        accounts_layout.setContentsMargins(0, 0, 0, 0)

        # Добавляем аккаунты
        for account in self.accounts:
            account_item = self._create_account_item(account)
            accounts_layout.addWidget(account_item)
            self.account_items.append(account_item)

        accounts_layout.addStretch()
        scroll.setWidget(accounts_widget)
        layout.addWidget(scroll)

    def _create_account_item(self, account: Dict) -> QFrame:
        """Создает элемент аккаунта"""
        frame = QFrame()
        frame.setObjectName("AccountItem")
        frame.setStyleSheet("""
            QFrame#AccountItem {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                padding: 8px;
                margin: 2px;
            }
            QFrame#AccountItem:hover {
                background: rgba(255, 255, 255, 0.08);
                border-color: rgba(255, 255, 255, 0.2);
            }
        """)

        layout = QHBoxLayout(frame)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(12)

        # Чекбокс (если нужен)
        if self.checkable:
            checkbox = QCheckBox()
            checkbox.setStyleSheet("""
                QCheckBox::indicator {
                    width: 18px;
                    height: 18px;
                    border-radius: 3px;
                    border: 2px solid rgba(255, 255, 255, 0.3);
                    background: rgba(255, 255, 255, 0.05);
                }
                QCheckBox::indicator:checked {
                    background: #3B82F6;
                    border-color: #3B82F6;
                }
                QCheckBox::indicator:checked::after {
                    content: "✓";
                    color: white;
                }
            """)
            layout.addWidget(checkbox)

        # Информация об аккаунте
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)

        # Имя аккаунта
        name_label = QLabel(account['name'])
        name_label.setStyleSheet("""
            font-size: 14px;
            font-weight: 600;
            color: #FFFFFF;
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
                font-size: 12px;
                color: rgba(255, 255, 255, 0.7);
            """)
            info_layout.addWidget(details_label)

        layout.addLayout(info_layout, 1)

        # Статус (если есть)
        if account.get('is_main_admin'):
            status_label = QLabel("👑 Главный админ")
            status_label.setStyleSheet("""
                background: rgba(34, 197, 94, 0.2);
                color: #22C55E;
                border: 1px solid rgba(34, 197, 94, 0.3);
                border-radius: 12px;
                padding: 4px 8px;
                font-size: 11px;
                font-weight: 500;
            """)
            layout.addWidget(status_label)

        return frame

    def get_selected_accounts(self) -> List[Dict]:
        """Возвращает список выбранных аккаунтов"""
        if not self.checkable:
            return []

        selected = []
        for i, item in enumerate(self.account_items):
            checkbox = item.findChild(QCheckBox)
            if checkbox and checkbox.isChecked():
                selected.append(self.accounts[i])

        return selected


class MainAdminsDialog(QDialog):
    """Диалог выбора главных админов для профиля"""

    accounts_selected = Signal(list)  # Сигнал для выбранных аккаунтов

    def __init__(self, parent, profile_name: str):
        super().__init__(parent)
        self.profile_name = profile_name
        self.selected_accounts = []

        self.setWindowTitle(f"Главные админы - {profile_name}")
        self.setFixedSize(800, 600)
        self.setModal(True)

        # Виджеты для вкладок
        self.available_widget = None
        self.admins_widget = None

        self._setup_styles()
        self._create_ui()
        self.load_accounts()

    def _setup_styles(self):
        """Настройка стилей"""
        self.setStyleSheet("""
            QDialog {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 rgba(15, 23, 42, 0.98),
                    stop: 1 rgba(30, 41, 59, 0.95)
                );
                border: 2px solid rgba(255, 255, 255, 0.1);
                border-radius: 16px;
                backdrop-filter: blur(20px);
            }

            QLabel#DialogIcon {
                font-size: 32px;
                background: rgba(251, 191, 36, 0.1);
                border-radius: 24px;
                border: 2px solid rgba(251, 191, 36, 0.3);
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

            QTabWidget::pane {
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                background: rgba(255, 255, 255, 0.02);
            }

            QTabBar::tab {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                padding: 10px 20px;
                margin-right: 2px;
                color: rgba(255, 255, 255, 0.7);
                font-size: 13px;
                font-weight: 500;
            }

            QTabBar::tab:selected {
                background: rgba(251, 191, 36, 0.2);
                border-color: rgba(251, 191, 36, 0.4);
                color: #FFFFFF;
            }

            QTabBar::tab:hover:!selected {
                background: rgba(255, 255, 255, 0.08);
                border-color: rgba(255, 255, 255, 0.2);
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

            QPushButton#ConfirmButton {
                background: #FBBF24;
                border: 1px solid #FBBF24;
                border-radius: 8px;
                color: #000000;
                font-size: 14px;
                font-weight: 600;
                padding: 12px 24px;
            }

            QPushButton#ConfirmButton:hover {
                background: #F59E0B;
                border-color: #F59E0B;
            }

            QPushButton#SecondaryButton {
                background: rgba(251, 191, 36, 0.2);
                border: 1px solid rgba(251, 191, 36, 0.5);
                border-radius: 8px;
                color: #FFFFFF;
                font-size: 14px;
                font-weight: 500;
                padding: 10px 20px;
            }

            QPushButton#SecondaryButton:hover {
                background: rgba(251, 191, 36, 0.3);
                border-color: rgba(251, 191, 36, 0.7);
            }
        """)

    def _create_ui(self):
        """Создает UI диалога"""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(24, 24, 24, 24)

        # Заголовок
        self._create_header(layout)

        # Вкладки с аккаунтами
        self._create_tabs(layout)

        # Кнопки
        self._create_buttons(layout)

    def _create_header(self, layout):
        """Создает заголовок диалога"""
        header_layout = QHBoxLayout()
        header_layout.setSpacing(15)

        # Иконка
        icon_label = QLabel("👑")
        icon_label.setObjectName("DialogIcon")
        icon_label.setFixedSize(48, 48)
        icon_label.setAlignment(Qt.AlignCenter)

        # Заголовок и описание
        text_layout = QVBoxLayout()

        title_label = QLabel(f"Главные админы - {self.profile_name}")
        title_label.setObjectName("DialogTitle")

        desc_label = QLabel(
            "Выберите аккаунты, которые станут главными админами в чатах.\n"
            f"Выбранные аккаунты будут перемещены в папку '{self.profile_name}/Админы/'"
        )
        desc_label.setObjectName("DialogDescription")
        desc_label.setWordWrap(True)

        text_layout.addWidget(title_label)
        text_layout.addWidget(desc_label)

        header_layout.addWidget(icon_label)
        header_layout.addLayout(text_layout, 1)

        layout.addLayout(header_layout)

    def _create_tabs(self, layout):
        """Создает вкладки с аккаунтами"""
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

    def _create_buttons(self, layout):
        """Создает кнопки диалога"""
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(12)

        # Кнопка выбрать все
        self.select_all_btn = QPushButton("Выбрать все")
        self.select_all_btn.setObjectName("SecondaryButton")
        self.select_all_btn.clicked.connect(self._select_all)

        # Кнопка снять с должности
        self.remove_admin_btn = QPushButton("Снять с должности")
        self.remove_admin_btn.setObjectName("SecondaryButton")
        self.remove_admin_btn.clicked.connect(self._remove_main_admins)

        buttons_layout.addWidget(self.select_all_btn)
        buttons_layout.addWidget(self.remove_admin_btn)
        buttons_layout.addStretch()

        # Кнопка отмены
        cancel_btn = QPushButton("Отменить")
        cancel_btn.setObjectName("CancelButton")
        cancel_btn.clicked.connect(self.reject)

        # Кнопка подтверждения
        self.confirm_btn = QPushButton("Назначить админами")
        self.confirm_btn.setObjectName("ConfirmButton")
        self.confirm_btn.clicked.connect(self._confirm_selection)

        buttons_layout.addWidget(cancel_btn)
        buttons_layout.addWidget(self.confirm_btn)

        layout.addLayout(buttons_layout)

    def load_accounts(self):
        """Загружает списки аккаунтов"""
        try:
            # Очищаем вкладки
            self.tabs.clear()

            # Загружаем доступные аккаунты
            available_accounts = self._load_available_accounts()

            # Загружаем существующих главных админов
            main_admins = self._load_main_admins()

            # Создаем вкладку с доступными аккаунтами
            if available_accounts:
                available_widget = AccountListWidget(
                    "Аккаунты, которые могут стать главными админами",
                    available_accounts,
                    checkable=True
                )
                self.tabs.addTab(available_widget, f"🟢 Доступные ({len(available_accounts)})")
                self.available_widget = available_widget

            # Создаем вкладку с главными админами
            if main_admins:
                admins_widget = AccountListWidget(
                    "Текущие главные админы профиля",
                    main_admins,
                    checkable=True
                )
                self.tabs.addTab(admins_widget, f"👑 Главные админы ({len(main_admins)})")
                self.admins_widget = admins_widget

            # Если нет доступных аккаунтов
            if not available_accounts:
                empty_label = QLabel("Нет доступных аккаунтов для назначения главными админами")
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
                    # Проверяем что аккаунт не является главным админом
                    if not self._is_main_admin(name):
                        available.append({
                            'name': name,
                            'phone': account_data.info.get('phone', ''),
                            'full_name': account_data.info.get('full_name', ''),
                            'is_main_admin': False,
                            'account_data': account_data
                        })

            logger.info(f"📋 Загружено доступных аккаунтов: {len(available)}")
            return available

        except Exception as e:
            logger.error(f"❌ Ошибка загрузки доступных аккаунтов: {e}")
            return []

    def _load_main_admins(self) -> List[Dict]:
        """Загружает главных админов из папки профиля"""
        try:
            admins_folder = self._get_profile_admins_folder()

            if not admins_folder or not admins_folder.exists():
                return []

            admins = []

            # Сканируем папку Админы
            for session_file in admins_folder.glob("*.session"):
                json_file = session_file.with_suffix(".json")

                if json_file.exists():
                    import json
                    try:
                        with open(json_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)

                        admins.append({
                            'name': session_file.stem,
                            'phone': data.get('phone', ''),
                            'full_name': f"{data.get('first_name', '')} {data.get('last_name', '')}".strip(),
                            'is_main_admin': True
                        })
                    except Exception as e:
                        logger.error(f"❌ Ошибка чтения {json_file}: {e}")

            logger.info(f"👑 Загружено главных админов: {len(admins)}")
            return admins

        except Exception as e:
            logger.error(f"❌ Ошибка загрузки главных админов: {e}")
            return []

    def _get_profile_admins_folder(self):
        from paths import get_profile_admins_folder
        return get_profile_admins_folder(self.profile_name)

    def _is_main_admin(self, account_name: str) -> bool:
        """Проверяет является ли аккаунт главным админом"""
        admins_folder = self._get_profile_admins_folder()
        if not admins_folder:
            return False

        session_file = admins_folder / f"{account_name}.session"
        return session_file.exists()

    def _select_all(self):
        """Выбирает все аккаунты на текущей вкладке"""
        current_tab = self.tabs.currentWidget()

        if isinstance(current_tab, AccountListWidget) and current_tab.checkable:
            for item in current_tab.account_items:
                checkbox = item.findChild(QCheckBox)
                if checkbox:
                    checkbox.setChecked(True)

    def _remove_main_admins(self):
        """Снимает выбранных админов с должности"""
        if not hasattr(self, 'admins_widget'):
            from gui.notifications import show_info
            show_info(
                "Снятие с должности",
                "Нет главных админов для снятия с должности"
            )
            return

        selected_admins = self.admins_widget.get_selected_accounts()

        if not selected_admins:
            from gui.notifications import show_warning
            show_warning(
                "Снятие с должности",
                "Выберите админов для снятия с должности на вкладке 'Главные админы'"
            )
            return

        # Снимаем выбранных админов с должности
        success_count = 0
        failed_accounts = []

        for account in selected_admins:
            account_name = account['name']
            success = self._remove_admin_account(account_name)

            if success:
                success_count += 1
                logger.info(f"🔄 Аккаунт {account_name} снят с должности главного админа")
            else:
                failed_accounts.append(account_name)
                logger.error(f"❌ Не удалось снять {account_name} с должности")

        # ИСПРАВЛЕНО: Обновляем AccountManager если он есть
        if success_count > 0:
            self._update_account_manager()

        # Показываем результат
        if failed_accounts:
            from gui.notifications import show_error
            show_error(
                "Ошибки при снятии",
                f"Снято с должности: {success_count}, ошибок: {len(failed_accounts)}\n"
                f"Не удалось снять: {', '.join(failed_accounts[:3])}" +
                (f" и еще {len(failed_accounts) - 3}" if len(failed_accounts) > 3 else "")
            )
        else:
            from gui.notifications import show_success
            show_success(
                "Админы сняты с должности",
                f"🔄 Успешно снято с должности {success_count} админ(ов)\n"
                f"Аккаунты возвращены в папку 'Трафик'"
            )

        # Перезагружаем данные
        self.load_accounts()

    def _confirm_selection(self):
        """Подтверждает выбор аккаунтов"""
        if hasattr(self, 'available_widget'):
            self.selected_accounts = self.available_widget.get_selected_accounts()

            if not self.selected_accounts:
                from gui.notifications import show_warning
                show_warning(
                    "Выбор админов",
                    "Выберите хотя бы один аккаунт для назначения главным админом"
                )
                return

            # Назначаем выбранные аккаунты главными админами
            success_count = 0
            failed_accounts = []

            for account in self.selected_accounts:
                account_name = account['name']
                success = self._assign_main_admin(account)

                if success:
                    success_count += 1
                    logger.info(f"👑 Аккаунт {account_name} назначен главным админом")
                else:
                    failed_accounts.append(account_name)
                    logger.error(f"❌ Не удалось назначить {account_name} главным админом")

            # ИСПРАВЛЕНО: Обновляем AccountManager если он есть
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
                    "Главные админы назначены",
                    f"👑 Успешно назначено {success_count} главных админов\n"
                    f"Аккаунты перемещены в папку '{self.profile_name}/Админы/'"
                )

                # Эмитим сигнал с выбранными аккаунтами
                self.accounts_selected.emit(self.selected_accounts)
                self.accept()

    def _assign_main_admin(self, account: Dict) -> bool:
        """ИСПРАВЛЕНО: Назначает аккаунт главным админом через paths.py"""
        try:
            account_name = account['name']
            logger.info(f"👑 Назначаем главным админом: {account_name}")

            # Получаем пути к файлам аккаунта
            from src.accounts.manager import _account_manager
            account_data = _account_manager.traffic_accounts.get(account_name)

            if not account_data:
                logger.error(f"❌ Аккаунт {account_name} не найден в трафике")
                return False

            session_src = account_data.account.session_path
            json_src = account_data.account.json_path

            if not session_src.exists() or not json_src.exists():
                logger.error(f"❌ Файлы аккаунта {account_name} не найдены")
                return False

            # ИСПОЛЬЗУЕМ ФУНКЦИЮ ИЗ paths.py!
            from paths import move_account_to_main_admins
            success = move_account_to_main_admins(
                self.profile_name,
                account_name,
                session_src,
                json_src
            )

            if success:
                logger.info(f"✅ Аккаунт {account_name} перемещен в папку админов")
            else:
                logger.error(f"❌ Не удалось переместить {account_name} в папку админов")

            return success

        except Exception as e:
            logger.error(f"❌ Ошибка назначения главным админом {account['name']}: {e}")
            return False

    def _remove_admin_account(self, account_name: str) -> bool:
        """ИСПРАВЛЕНО: Снимает аккаунт с должности главного админа через paths.py"""
        try:
            logger.info(f"🔄 Снимаем с должности главного админа: {account_name}")

            # ИСПОЛЬЗУЕМ ФУНКЦИЮ ИЗ paths.py!
            from paths import move_main_admin_to_traffic
            success = move_main_admin_to_traffic(self.profile_name, account_name)

            if success:
                logger.info(f"✅ Аккаунт {account_name} возвращен в трафик")
            else:
                logger.error(f"❌ Не удалось вернуть {account_name} в трафик")

            return success

        except Exception as e:
            logger.error(f"❌ Ошибка снятия с должности {account_name}: {e}")
            return False

    def _update_account_manager(self):
        """ИСПРАВЛЕНО: Обновляет AccountManager после изменений"""
        try:
            from src.accounts.manager import _account_manager

            if _account_manager:
                # ИСПРАВЛЕНО: Используем scan_all_folders вместо reload_accounts
                import asyncio

                # Создаем новую задачу если нет активного цикла событий
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # Если цикл уже запущен, создаем задачу
                        asyncio.create_task(_account_manager.scan_all_folders())
                    else:
                        # Если цикл не запущен, запускаем синхронно
                        asyncio.run(_account_manager.scan_all_folders())
                except RuntimeError:
                    # Если нет цикла событий, создаем новый
                    asyncio.run(_account_manager.scan_all_folders())

                logger.info("🔄 AccountManager обновлен")

        except Exception as e:
            logger.error(f"❌ Ошибка обновления AccountManager: {e}")


def show_main_admins_dialog(parent, profile_name: str) -> List[Dict]:
    """
    Показывает диалог выбора главных админов

    Args:
        parent: Родительский виджет
        profile_name: Имя профиля

    Returns:
        List[Dict]: Список выбранных аккаунтов или пустой список
    """
    dialog = MainAdminsDialog(parent, profile_name)

    selected = []

    def on_accounts_selected(accounts):
        nonlocal selected
        selected = accounts

    dialog.accounts_selected.connect(on_accounts_selected)

    if dialog.exec() == QDialog.Accepted:
        return selected

    return []