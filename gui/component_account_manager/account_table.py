# gui/component_account_manager/account_table.py - ПОЛНОСТЬЮ РАБОЧАЯ ВЕРСИЯ

"""
Компонент таблицы аккаунтов с полноценной пагинацией
"""
from typing import List
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QHeaderView, QApplication, QGraphicsOpacityEffect,
    QComboBox, QSpacerItem, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, Signal
from PySide6.QtGui import QColor, QCursor
from loguru import logger

from gui.handlers import TableActionHandler

CHECKBOX_STYLE_ELEGANT = """
        QPushButton#RowCheckbox {
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 6px;
            color: transparent;
        }
        QPushButton#RowCheckbox:checked {
            background: rgba(59, 130, 246, 0.9);
            border: 1px solid #3B82F6;
            box-shadow: 0 0 8px rgba(59, 130, 246, 0.3);
        }
        QPushButton#RowCheckbox:checked::after {
            content: "✓";
            color: white;
            font-size: 11px;
            font-weight: 600;
        }
        QPushButton#RowCheckbox:hover {
            background: rgba(59, 130, 246, 0.1);
            border: 1px solid rgba(59, 130, 246, 0.3);
        }
    """


class AccountTableWidget(QWidget):
    """Виджет таблицы аккаунтов с пагинацией"""

    # Сигнал для запроса данных с пагинацией
    data_requested = Signal(str, str, int, int)  # category, status, page, per_page

    def __init__(self, config):
        """
        config: словарь с настройками
        {
            'title': 'Заголовок таблицы',
            'add_button_text': 'Текст кнопки добавления',
            'demo_data': [[...], [...]]  # Данные для таблицы
            'category': 'traffic' или 'sales',
            'current_status': 'active' или другой статус
        }
        """
        super().__init__()
        self.setObjectName("AccountTableWidget")
        self.config = config

        # Сохраняем все нужные атрибуты как свойства класса
        self.current_status = config.get('current_status', 'active')
        self.category = config.get('category', 'traffic')

        # Параметры пагинации
        self.current_page = 1
        self.per_page = 10  # По умолчанию 10 элементов на странице
        self.total_items = 0
        self.total_pages = 0
        self.all_data = []  # Все данные для пагинации

        # Основной layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)

        # Создаем компоненты
        self._create_actions_bar(layout)
        self._create_table(layout)
        self._create_pagination_controls(layout)

        # Заполняем данными
        self._load_initial_data()

        # Начальная прозрачность для анимации
        effect = QGraphicsOpacityEffect()
        effect.setOpacity(0.0)
        self.setGraphicsEffect(effect)

        logger.info(f"📊 AccountTableWidget создан для {self.category}/{self.current_status}")

    def _create_actions_bar(self, layout):
        """Создает панель действий"""
        actions_container = QWidget()
        actions_container.setObjectName("ActionsContainer")
        actions_layout = QHBoxLayout(actions_container)
        actions_layout.setContentsMargins(0, 5, 0, 10)
        actions_layout.setSpacing(10)

        # Заголовок секции
        self.section_title = QLabel()
        self.section_title.setObjectName("SectionTitle")
        self.section_title.setStyleSheet("""
            QLabel#SectionTitle {
                font-size: 16px;
                font-weight: 600;
                color: rgba(255, 255, 255, 0.9);
            }
        """)
        self._update_section_title()

        # Кнопки массовых действий
        self.delete_btn = QPushButton("🗑️ Удалить")
        self.delete_btn.setObjectName("ActionButton")
        self.delete_btn.setFixedSize(100, 36)
        self.delete_btn.setStyleSheet("""
            QPushButton#ActionButton {
                background: rgba(255, 255, 255, 0.06);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 6px;
                color: rgba(255, 255, 255, 0.9);
                font-size: 13px;
                font-weight: 500;
            }
            QPushButton#ActionButton:hover {
                background: rgba(255, 255, 255, 0.12);
                border: 1px solid rgba(59, 130, 246, 0.5);
                color: #FFFFFF;
            }
        """)

        self.update_btn = QPushButton("🔄 Обновить")
        self.update_btn.setObjectName("ActionButton")
        self.update_btn.setFixedSize(110, 36)
        self.update_btn.setStyleSheet("""
            QPushButton#ActionButton {
                background: rgba(255, 255, 255, 0.06);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 6px;
                color: rgba(255, 255, 255, 0.9);
                font-size: 13px;
                font-weight: 500;
            }
            QPushButton#ActionButton:hover {
                background: rgba(255, 255, 255, 0.12);
                border: 1px solid rgba(59, 130, 246, 0.5);
                color: #FFFFFF;
            }
        """)

        self.move_btn = QPushButton("📦 Переместить")
        self.move_btn.setObjectName("ActionButton")
        self.move_btn.setFixedSize(130, 36)
        self.move_btn.setStyleSheet("""
            QPushButton#ActionButton {
                background: rgba(255, 255, 255, 0.06);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 6px;
                color: rgba(255, 255, 255, 0.9);
                font-size: 13px;
                font-weight: 500;
            }
            QPushButton#ActionButton:hover {
                background: rgba(255, 255, 255, 0.12);
                border: 1px solid rgba(59, 130, 246, 0.5);
                color: #FFFFFF;
            }
        """)

        self.archive_btn = QPushButton("📦 Архивировать")
        self.archive_btn.setObjectName("ActionButton")
        self.archive_btn.setFixedSize(140, 36)
        self.archive_btn.setStyleSheet("""
                    QPushButton#ActionButton {
                        background: rgba(255, 255, 255, 0.06);
                        border: 1px solid rgba(255, 255, 255, 0.15);
                        border-radius: 6px;
                        color: rgba(255, 255, 255, 0.9);
                        font-size: 13px;
                        font-weight: 500;
                    }
                    QPushButton#ActionButton:hover {
                        background: rgba(255, 255, 255, 0.12);
                        border: 1px solid rgba(59, 130, 246, 0.5);
                        color: #FFFFFF;
                    }
                """)

        # Селектор количества элементов на странице
        per_page_label = QLabel("Показать:")
        per_page_label.setObjectName("PerPageLabel")
        per_page_label.setStyleSheet("""
            QLabel#PerPageLabel {
                color: rgba(255, 255, 255, 0.8);
                font-size: 13px;
                font-weight: 500;
            }
        """)

        self.per_page_combo = QComboBox()
        self.per_page_combo.setObjectName("PerPageCombo")
        self.per_page_combo.addItems(["10", "25", "50", "100", "Все"])
        self.per_page_combo.setCurrentText("10")
        self.per_page_combo.setFixedSize(80, 36)
        self.per_page_combo.setStyleSheet("""
            QComboBox#PerPageCombo {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 6px;
                padding: 4px 8px;
                color: rgba(255, 255, 255, 0.9);
                font-size: 13px;
            }
            QComboBox#PerPageCombo:hover {
                border-color: rgba(59, 130, 246, 0.5);
                background: rgba(255, 255, 255, 0.08);
            }
            QComboBox#PerPageCombo::drop-down {
                border: none;
                padding-right: 8px;
            }
            QComboBox#PerPageCombo QAbstractItemView {
                background: rgba(30, 30, 30, 0.95);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 6px;
                selection-background-color: rgba(59, 130, 246, 0.3);
                color: rgba(255, 255, 255, 0.9);
                padding: 4px;
            }
        """)
        self.per_page_combo.currentTextChanged.connect(self._on_per_page_changed)

        # Кнопка добавления
        self.add_btn = QPushButton(self.config.get('add_button_text', '+ Добавить'))
        self.add_btn.setObjectName("AddButton")
        self.add_btn.setFixedSize(160, 36)
        self.add_btn.setStyleSheet("""
            QPushButton#AddButton {
                background: #3B82F6;
                border: none;
                border-radius: 6px;
                color: #FFFFFF;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton#AddButton:hover {
                background: #2563EB;
            }
        """)

        # Размещение элементов
        actions_layout.addWidget(self.section_title)
        actions_layout.addWidget(self.delete_btn)
        actions_layout.addWidget(self.update_btn)
        actions_layout.addWidget(self.move_btn)
        actions_layout.addWidget(self.archive_btn)
        actions_layout.addStretch()
        actions_layout.addWidget(per_page_label)
        actions_layout.addWidget(self.per_page_combo)
        actions_layout.addWidget(self.add_btn)

        layout.addWidget(actions_container)

        # Подключаем обработчики
        self.action_handler = TableActionHandler(self)
        self.delete_btn.clicked.connect(self.action_handler.handle_delete_action)
        self.update_btn.clicked.connect(self.action_handler.handle_refresh_action)
        self.move_btn.clicked.connect(self.action_handler.handle_move_action)
        self.archive_btn.clicked.connect(self.action_handler.handle_archive_action)

    def _create_table(self, layout):
        """Создает таблицу"""
        table_container = QWidget()
        table_container.setObjectName("TableContainer")
        table_layout = QVBoxLayout(table_container)
        table_layout.setContentsMargins(0, 0, 0, 0)

        # Создаем таблицу
        self.table = QTableWidget()
        self.table.setObjectName("ModernTable")

        # ВАЖНО: Устанавливаем заголовки СРАЗУ после создания таблицы
        headers = [
            "",  # Чекбоксы
            "Название аккаунта",
            "🌍 Гео",
            "📅 Дней\nсоздан",  # Перенос строки для длинного заголовка
            "📊 Статус",
            "👤 Имя",
            "📱 Телефон",
            "💎 Премиум"
        ]

        # Устанавливаем количество колонок
        self.table.setColumnCount(len(headers))

        # Устанавливаем заголовки
        self.table.setHorizontalHeaderLabels(headers)

        logger.info(f"📊 Создана таблица с {len(headers)} колонками")

        # Настройки таблицы
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.verticalHeader().setDefaultSectionSize(60)

        # Настройка колонок
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)  # Чекбоксы
        header.setSectionResizeMode(1, QHeaderView.Stretch)  # Название
        header.setSectionResizeMode(2, QHeaderView.Fixed)  # Гео
        header.setSectionResizeMode(3, QHeaderView.Fixed)  # Дней создан
        header.setSectionResizeMode(4, QHeaderView.Stretch)  # Статус
        header.setSectionResizeMode(5, QHeaderView.Stretch)  # Имя
        header.setSectionResizeMode(6, QHeaderView.Fixed)  # Телефон
        header.setSectionResizeMode(7, QHeaderView.Fixed)  # Премиум

        self.table.setColumnWidth(0, 50)  # Чекбоксы
        self.table.setColumnWidth(1, 120)  # Название аккаунта - ДОБАВЬТЕ ЭТУ СТРОКУ
        self.table.setColumnWidth(2, 90)  # Гео
        self.table.setColumnWidth(3, 200)  # Дней создан
        self.table.setColumnWidth(4, 100)  # Статус - ДОБАВЬТЕ ЭТУ СТРОКУ
        self.table.setColumnWidth(5, 120)  # Имя - ДОБАВЬТЕ ЭТУ СТРОКУ
        self.table.setColumnWidth(6, 200)  # Телефон
        self.table.setColumnWidth(7, 160)  # Премиум

        # Создаем главный чекбокс
        self._create_master_checkbox()

        table_layout.addWidget(self.table)
        layout.addWidget(table_container)

    def _create_pagination_controls(self, layout):
        """Создает элементы управления пагинацией"""
        pagination_container = QWidget()
        pagination_container.setObjectName("PaginationContainer")
        pag_layout = QHBoxLayout(pagination_container)
        pag_layout.setContentsMargins(0, 10, 0, 0)
        pag_layout.setSpacing(15)

        # Информация о записях
        self.info_label = QLabel()
        self.info_label.setObjectName("PaginationInfo")
        self.info_label.setStyleSheet("""
            QLabel#PaginationInfo {
                color: rgba(255, 255, 255, 0.6);
                font-size: 13px;
                font-weight: 400;
            }
        """)

        # Кнопки навигации
        nav_button_style = """
            QPushButton#PaginationNavButton {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                color: rgba(255, 255, 255, 0.8);
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton#PaginationNavButton:hover:enabled {
                background: rgba(59, 130, 246, 0.2);
                border-color: rgba(59, 130, 246, 0.5);
                color: #FFFFFF;
            }
            QPushButton#PaginationNavButton:pressed:enabled {
                background: rgba(59, 130, 246, 0.3);
            }
            QPushButton#PaginationNavButton:disabled {
                background: rgba(255, 255, 255, 0.02);
                border-color: rgba(255, 255, 255, 0.05);
                color: rgba(255, 255, 255, 0.3);
            }
        """

        self.first_btn = QPushButton("⏮️")
        self.first_btn.setObjectName("PaginationNavButton")
        self.first_btn.setFixedSize(36, 36)
        self.first_btn.setToolTip("Первая страница")
        self.first_btn.setStyleSheet(nav_button_style)
        self.first_btn.clicked.connect(self._go_to_first_page)

        self.prev_btn = QPushButton("◀️")
        self.prev_btn.setObjectName("PaginationNavButton")
        self.prev_btn.setFixedSize(36, 36)
        self.prev_btn.setToolTip("Предыдущая страница")
        self.prev_btn.setStyleSheet(nav_button_style)
        self.prev_btn.clicked.connect(self._go_to_prev_page)

        # Информация о текущей странице
        self.page_label = QLabel()
        self.page_label.setObjectName("PageLabel")
        self.page_label.setStyleSheet("""
            QLabel#PageLabel {
                color: rgba(255, 255, 255, 0.9);
                font-size: 14px;
                font-weight: 500;
                padding: 0 12px;
                min-width: 80px;
            }
        """)
        self.page_label.setAlignment(Qt.AlignCenter)

        self.next_btn = QPushButton("▶️")
        self.next_btn.setObjectName("PaginationNavButton")
        self.next_btn.setFixedSize(36, 36)
        self.next_btn.setToolTip("Следующая страница")
        self.next_btn.setStyleSheet(nav_button_style)
        self.next_btn.clicked.connect(self._go_to_next_page)

        self.last_btn = QPushButton("⏭️")
        self.last_btn.setObjectName("PaginationNavButton")
        self.last_btn.setFixedSize(36, 36)
        self.last_btn.setToolTip("Последняя страница")
        self.last_btn.setStyleSheet(nav_button_style)
        self.last_btn.clicked.connect(self._go_to_last_page)

        # Размещение элементов
        pag_layout.addWidget(self.info_label)
        pag_layout.addStretch()
        pag_layout.addWidget(self.first_btn)
        pag_layout.addWidget(self.prev_btn)
        pag_layout.addWidget(self.page_label)
        pag_layout.addWidget(self.next_btn)
        pag_layout.addWidget(self.last_btn)

        layout.addWidget(pagination_container)

    def _create_master_checkbox(self):
        """Создает главный стильный чекбокс с галочкой в заголовке"""
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)

        self.master_checkbox = QPushButton()
        self.master_checkbox.setObjectName("MasterCheckbox")
        self.master_checkbox.setCheckable(True)
        self.master_checkbox.setFixedSize(20, 20)

        # Тот же стиль что и у обычных чекбоксов
        self.master_checkbox.setStyleSheet("""
            QPushButton#MasterCheckbox {
                background: rgba(255, 255, 255, 0.06);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 5px;
                color: white;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton#MasterCheckbox:checked {
                background: #3B82F6;
                border: 1px solid #2563EB;
            }
            QPushButton#MasterCheckbox:hover {
                background: rgba(59, 130, 246, 0.12);
                border: 1px solid rgba(59, 130, 246, 0.25);
            }
        """)

        # Функция для обновления текста главного чекбокса
        def update_master_checkbox_text():
            if self.master_checkbox.isChecked():
                self.master_checkbox.setText("✓")
            else:
                self.master_checkbox.setText("")

        # Подключаем обновление текста к изменению состояния
        self.master_checkbox.toggled.connect(update_master_checkbox_text)

        # Изначально устанавливаем пустой текст
        self.master_checkbox.setText("")

        self.master_checkbox.clicked.connect(self._toggle_all_checkboxes)

        header_layout.addStretch()
        header_layout.addWidget(self.master_checkbox)
        header_layout.addStretch()

        # Размещаем в заголовке
        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.setInterval(200)
        timer.timeout.connect(lambda: self._place_header_checkbox(header_widget))
        timer.start()

    def _place_header_checkbox(self, widget):
        """Размещает чекбокс в заголовке"""
        header = self.table.horizontalHeader()
        x = header.sectionPosition(0)
        width = header.sectionSize(0)
        widget.setParent(header)
        widget.setGeometry(x, 0, width, header.height())
        widget.show()

    def _load_initial_data(self):
        """Загружает начальные данные"""
        demo_data = self.config.get('demo_data', [])
        self.all_data = demo_data
        self.total_items = len(demo_data)

        self._calculate_pagination()
        self._update_table_for_current_page()

        logger.info(f"✅ Начальные данные загружены: {self.total_items} записей")

    def _calculate_pagination(self):
        """Рассчитывает параметры пагинации"""
        if self.per_page == -1:  # "Все"
            self.total_pages = 1
            self.current_page = 1
        else:
            self.total_pages = max(1, (self.total_items + self.per_page - 1) // self.per_page)
            if self.current_page > self.total_pages:
                self.current_page = self.total_pages

        self._update_pagination_info()
        self._update_pagination_buttons()

    def _update_pagination_info(self):
        """Обновляет информацию о пагинации"""
        if self.total_items == 0:
            self.info_label.setText("Нет записей")
            self.page_label.setText("0 / 0")
            return

        if self.per_page == -1:  # "Все"
            self.info_label.setText(f"Показано все {self.total_items} записей")
            self.page_label.setText("1 / 1")
        else:
            start_item = (self.current_page - 1) * self.per_page + 1
            end_item = min(self.current_page * self.per_page, self.total_items)

            self.info_label.setText(f"Показано {start_item}-{end_item} из {self.total_items} записей")
            self.page_label.setText(f"{self.current_page} / {self.total_pages}")

    def _update_pagination_buttons(self):
        """Обновляет состояние кнопок пагинации"""
        if self.per_page == -1:  # "Все"
            for btn in [self.first_btn, self.prev_btn, self.next_btn, self.last_btn]:
                btn.setEnabled(False)
        else:
            self.first_btn.setEnabled(self.current_page > 1)
            self.prev_btn.setEnabled(self.current_page > 1)
            self.next_btn.setEnabled(self.current_page < self.total_pages)
            self.last_btn.setEnabled(self.current_page < self.total_pages)

    def _get_current_page_data(self):
        """Возвращает данные для текущей страницы"""
        if self.per_page == -1:  # "Все"
            return self.all_data

        start_idx = (self.current_page - 1) * self.per_page
        end_idx = start_idx + self.per_page
        return self.all_data[start_idx:end_idx]

    def _update_table_for_current_page(self):
        """Обновляет таблицу для текущей страницы"""
        page_data = self._get_current_page_data()
        self._fill_table_with_data(page_data)

    def _fill_table_with_data(self, data):
        """Заполняет таблицу данными"""
        # Очищаем таблицу
        self.table.clearContents()
        self.table.setRowCount(len(data))

        if len(data) == 0:
            logger.info("Нет данных для отображения")
            return

        # Заполняем таблицу данными
        for row_idx, row_data in enumerate(data):
            # Создаем чекбокс для первой колонки
            self._create_row_checkbox(row_idx)

            # Заполняем остальные колонки (начиная с 1)
            for col_idx, cell_value in enumerate(row_data):
                if col_idx >= 7:  # Максимум 7 колонок данных
                    break

                # Создаем элемент таблицы
                item = QTableWidgetItem(str(cell_value))
                item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)

                # Применяем стили
                self._apply_cell_styling(item, col_idx + 1, cell_value)

                # Размещаем в таблице (col_idx + 1 для пропуска колонки чекбоксов)
                self.table.setItem(row_idx, col_idx + 1, item)

        # Обновляем отображение
        self.table.viewport().update()
        QApplication.processEvents()

        logger.info(f"✅ Таблица заполнена: {len(data)} строк")

    def _create_row_checkbox(self, row):
        """Создает стильный чекбокс с галочкой для строки"""
        checkbox_container = QWidget()
        checkbox_layout = QHBoxLayout(checkbox_container)
        checkbox_layout.setContentsMargins(0, 0, 0, 0)

        checkbox = QPushButton()
        checkbox.setObjectName("RowCheckbox")
        checkbox.setCheckable(True)
        checkbox.setFixedSize(20, 20)
        checkbox.setCursor(QCursor(Qt.PointingHandCursor))

        # Устанавливаем стиль и изначально пустой текст
        checkbox.setStyleSheet("""
            QPushButton#RowCheckbox {
                background: rgba(255, 255, 255, 0.06);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 5px;
                color: white;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton#RowCheckbox:checked {
                background: #3B82F6;
                border: 1px solid #2563EB;
            }
            QPushButton#RowCheckbox:hover {
                background: rgba(59, 130, 246, 0.12);
                border: 1px solid rgba(59, 130, 246, 0.25);
            }
        """)

        # Функция для обновления текста чекбокса
        def update_checkbox_text():
            if checkbox.isChecked():
                checkbox.setText("✓")
            else:
                checkbox.setText("")

        # Подключаем обновление текста к изменению состояния
        checkbox.toggled.connect(update_checkbox_text)

        # Изначально устанавливаем пустой текст
        checkbox.setText("")

        checkbox.clicked.connect(lambda checked, r=row: self._handle_checkbox_click(r, checked))

        checkbox_layout.addStretch()
        checkbox_layout.addWidget(checkbox)
        checkbox_layout.addStretch()

        self.table.setCellWidget(row, 0, checkbox_container)

    def _apply_cell_styling(self, item, col, value):
        """Применяет стили к ячейке"""
        # Стиль для статуса (колонка 4)
        if col == 4:
            status_text = str(value)
            if "Активный" in status_text or "готов" in status_text:
                item.setForeground(QColor("#10B981"))
            elif "Мертвый" in status_text:
                item.setForeground(QColor("#EF4444"))
            elif "Заморожен" in status_text:
                item.setForeground(QColor("#F59E0B"))
            elif "Неверный" in status_text:
                item.setForeground(QColor("#6B7280"))
            elif "Регистрация" in status_text:
                item.setForeground(QColor("#3B82F6"))
            else:
                item.setForeground(QColor("#8B5CF6"))

        # Стиль для премиум статуса (колонка 7)
        elif col == 7:
            if value == "✅":
                item.setForeground(QColor("#10B981"))
            elif value == "❌":
                item.setForeground(QColor("#EF4444"))
            else:
                item.setForeground(QColor("#FFFFFF"))

        # Стандартный стиль для остальных колонок
        else:
            item.setForeground(QColor("#FFFFFF"))

    # Обработчики событий пагинации
    def _on_per_page_changed(self, value):
        """Обработчик изменения количества элементов на странице"""
        if value == "Все":
            self.per_page = -1
        else:
            self.per_page = int(value)

        self.current_page = 1
        self._calculate_pagination()
        self._update_table_for_current_page()

    def _go_to_first_page(self):
        """Переход на первую страницу"""
        self.current_page = 1
        self._calculate_pagination()
        self._update_table_for_current_page()

    def _go_to_prev_page(self):
        """Переход на предыдущую страницу"""
        if self.current_page > 1:
            self.current_page -= 1
            self._calculate_pagination()
            self._update_table_for_current_page()

    def _go_to_next_page(self):
        """Переход на следующую страницу"""
        if self.current_page < self.total_pages:
            self.current_page += 1
            self._calculate_pagination()
            self._update_table_for_current_page()

    def _go_to_last_page(self):
        """Переход на последнюю страницу"""
        self.current_page = self.total_pages
        self._calculate_pagination()
        self._update_table_for_current_page()

    # Вспомогательные методы
    def _toggle_all_checkboxes(self):
        """Переключает все чекбоксы на текущей странице - ОБНОВЛЕННАЯ ВЕРСИЯ"""
        master_checked = self.master_checkbox.isChecked()

        for row in range(self.table.rowCount()):
            checkbox_container = self.table.cellWidget(row, 0)
            if checkbox_container:
                checkbox = checkbox_container.findChild(QPushButton)
                if checkbox:
                    checkbox.setChecked(master_checked)
                    # Обновляем текст галочки
                    if master_checked:
                        checkbox.setText("✓")
                    else:
                        checkbox.setText("")

    def _handle_checkbox_click(self, row, checked):
        """Обработка клика по чекбоксу"""
        self.last_clicked_row = row
        self._update_master_checkbox()

    def _update_master_checkbox(self):
        """Обновляет состояние главного чекбокса - ОБНОВЛЕННАЯ ВЕРСИЯ"""
        total_rows = self.table.rowCount()
        if total_rows == 0:
            return

        checked_rows = 0
        for row in range(total_rows):
            checkbox_container = self.table.cellWidget(row, 0)
            if checkbox_container:
                checkbox = checkbox_container.findChild(QPushButton)
                if checkbox and checkbox.isChecked():
                    checked_rows += 1

        # Обновляем состояние и текст главного чекбокса
        if checked_rows == total_rows:
            self.master_checkbox.setChecked(True)
            self.master_checkbox.setText("✓")
        elif checked_rows == 0:
            self.master_checkbox.setChecked(False)
            self.master_checkbox.setText("")
        else:
            # Частичное выделение - можно показать минус или оставить пустым
            self.master_checkbox.setChecked(False)
            self.master_checkbox.setText("−")  # Показываем минус для частичного выделения

    def _update_section_title(self):
        """Обновляет заголовок секции"""
        if hasattr(self, 'section_title'):
            try:
                from src.accounts.manager import get_status_display_name
                folder_name = get_status_display_name(self.category, self.current_status)
                icon = "🚀" if self.category == "traffic" else "💰"
                self.section_title.setText(f"{icon} {folder_name}")
            except:
                self.section_title.setText(f"📋 {self.current_status}")

    # Публичные методы для внешнего использования
    def get_selected_account_names(self) -> List[str]:
        """Возвращает список имен выбранных аккаунтов"""
        selected_rows = self.get_selected_rows()
        account_names = []
        for row in selected_rows:
            item = self.table.item(row, 1)  # Колонка с именем аккаунта
            if item:
                account_names.append(item.text())
        return account_names

    def get_selected_rows(self):
        """Возвращает список выбранных строк"""
        selected = []
        for row in range(self.table.rowCount()):
            checkbox_container = self.table.cellWidget(row, 0)
            if checkbox_container:
                checkbox = checkbox_container.findChild(QPushButton)
                if checkbox and checkbox.isChecked():
                    selected.append(row)
        return selected

    def get_table_category(self) -> str:
        """Возвращает категорию таблицы"""
        return self.category

    def get_current_status(self) -> str:
        """Получает текущий статус (папку) таблицы"""
        return self.current_status

    def set_current_status(self, status: str):
        """Устанавливает текущий статус (папку) для отображения"""
        self.current_status = status
        self.config['current_status'] = status
        self._update_section_title()
        self.refresh_data()

    def refresh_data(self):
        """Обновление данных таблицы"""
        try:
            from src.accounts.manager import get_table_data
            # Получаем ВСЕ данные для текущей папки (без лимита)
            new_data = get_table_data(self.category, self.current_status, limit=-1)
            self.all_data = new_data
            self.total_items = len(new_data)
            self.config['demo_data'] = new_data

            # Сбрасываем на первую страницу при обновлении
            self.current_page = 1
            self._calculate_pagination()
            self._update_table_for_current_page()

            logger.info(f"📊 Обновлены данные: {self.total_items} записей")

        except Exception as e:
            logger.error(f"❌ Ошибка refresh_data: {e}")

    def update_table_data(self, new_data):
        """Обновляет данные в таблице"""
        self.all_data = new_data
        self.total_items = len(new_data)
        self.config['demo_data'] = new_data

        # Сбрасываем на первую страницу при обновлении
        self.current_page = 1
        self._calculate_pagination()
        self._update_table_for_current_page()

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

    def get_pagination_info(self):
        """Возвращает информацию о пагинации"""
        return {
            'current_page': self.current_page,
            'total_pages': self.total_pages,
            'per_page': self.per_page,
            'total_items': self.total_items
        }