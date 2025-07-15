# TeleCRM/gui/components/account_table.py
"""
Компонент таблицы аккаунтов
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QHeaderView, QApplication, QGraphicsOpacityEffect
)
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QColor


class AccountTableWidget(QWidget):
    """Виджет таблицы аккаунтов"""

    def __init__(self, config):
        """
        config: словарь с настройками
        {
            'title': 'Заголовок таблицы',
            'add_button_text': 'Текст кнопки добавления',
            'demo_data': [[...], [...]]  # Данные для таблицы
        }
        """
        super().__init__()
        self.setObjectName("AccountTableWidget")
        self.config = config

        # Основной layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)

        # Создаем компоненты
        self._create_actions_bar(layout)
        self._create_table(layout)
        self._create_pagination(layout)

        # Заполняем данными
        self._fill_table_data()

        # Начальная прозрачность для анимации
        effect = QGraphicsOpacityEffect()
        effect.setOpacity(0.0)
        self.setGraphicsEffect(effect)

    def _create_actions_bar(self, layout):
        """Создает панель действий"""
        actions_container = QWidget()
        actions_container.setObjectName("ActionsContainer")
        actions_layout = QHBoxLayout(actions_container)
        actions_layout.setContentsMargins(0, 5, 0, 10)
        actions_layout.setSpacing(10)

        # Заголовок секции
        section_title = QLabel(self.config.get('title', '📋 Список аккаунтов'))
        section_title.setObjectName("SectionTitle")
        section_title.setStyleSheet("""
            QLabel#SectionTitle {
                font-size: 16px;
                font-weight: 600;
                color: rgba(255, 255, 255, 0.9);
            }
        """)

        # Кнопки массовых действий
        self.delete_btn = QPushButton("🗑️ Удалить")
        self.delete_btn.setObjectName("ActionButton")
        self.delete_btn.setFixedSize(100, 36)

        self.update_btn = QPushButton("🔄 Обновить")
        self.update_btn.setObjectName("ActionButton")
        self.update_btn.setFixedSize(110, 36)

        self.move_btn = QPushButton("📦 Переместить")
        self.move_btn.setObjectName("ActionButton")
        self.move_btn.setFixedSize(130, 36)

        self.archive_btn = QPushButton("📁 Архивировать")
        self.archive_btn.setObjectName("ActionButton")
        self.archive_btn.setFixedSize(140, 36)

        # Кнопка добавления
        self.add_btn = QPushButton(self.config.get('add_button_text', '+ Добавить'))
        self.add_btn.setObjectName("AddButton")
        self.add_btn.setFixedSize(160, 36)

        actions_layout.addWidget(section_title)
        actions_layout.addWidget(self.delete_btn)
        actions_layout.addWidget(self.update_btn)
        actions_layout.addWidget(self.move_btn)
        actions_layout.addWidget(self.archive_btn)
        actions_layout.addStretch()
        actions_layout.addWidget(self.add_btn)

        layout.addWidget(actions_container)

    def _create_table(self, layout):
        """Создает таблицу"""
        table_container = QWidget()
        table_container.setObjectName("TableContainer")
        table_layout = QVBoxLayout(table_container)
        table_layout.setContentsMargins(0, 0, 0, 0)

        # Создаем таблицу
        self.table = QTableWidget(10, 8)
        self.table.setObjectName("ModernTable")
        self.table.setHorizontalHeaderLabels([
            "",  # Чекбоксы
            "#",  # Номер
            "Название аккаунта",
            "🌍 Гео",
            "📅 Дней создан",
            "⏰ Последний онлайн",
            "👤 Имя",
            "💎 Премиум"
        ])

        # Настройки таблицы
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.verticalHeader().setDefaultSectionSize(60)

        # Настройка колонок
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)  # Чекбоксы
        header.setSectionResizeMode(1, QHeaderView.Fixed)  # Номер
        header.setSectionResizeMode(2, QHeaderView.Stretch)  # Название
        header.setSectionResizeMode(3, QHeaderView.Stretch)  # Гео
        header.setSectionResizeMode(4, QHeaderView.Stretch)  # Дней создан
        header.setSectionResizeMode(5, QHeaderView.Stretch)  # Последний онлайн
        header.setSectionResizeMode(6, QHeaderView.Stretch)  # Имя
        header.setSectionResizeMode(7, QHeaderView.Stretch)  # Премиум

        self.table.setColumnWidth(0, 50)  # Чекбоксы
        self.table.setColumnWidth(1, 60)  # Номера

        # Создаем главный чекбокс
        self._create_master_checkbox()

        table_layout.addWidget(self.table)
        layout.addWidget(table_container)

    def _create_master_checkbox(self):
        """Создает главный чекбокс в заголовке"""
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)

        self.master_checkbox = QPushButton()
        self.master_checkbox.setObjectName("MasterCheckbox")
        self.master_checkbox.setCheckable(True)
        self.master_checkbox.setFixedSize(24, 24)
        self.master_checkbox.setStyleSheet("""
            QPushButton#MasterCheckbox {
                background: rgba(255, 255, 255, 0.1);
                border: 2px solid rgba(255, 255, 255, 0.4);
                border-radius: 6px;
            }
            QPushButton#MasterCheckbox:checked {
                background: #3B82F6;
                border: 2px solid #3B82F6;
            }
            QPushButton#MasterCheckbox:hover {
                border: 2px solid #3B82F6;
                background: rgba(59, 130, 246, 0.3);
            }
        """)
        self.master_checkbox.clicked.connect(self._toggle_all_checkboxes)

        header_layout.addStretch()
        header_layout.addWidget(self.master_checkbox)
        header_layout.addStretch()

        # Размещаем в заголовке
        QTimer.singleShot(100, lambda: self._place_header_checkbox(header_widget))

    def _place_header_checkbox(self, widget):
        """Размещает чекбокс в заголовке"""
        header = self.table.horizontalHeader()
        x = header.sectionPosition(0)
        width = header.sectionSize(0)

        widget.setParent(header)
        widget.setGeometry(x, 0, width, header.height())
        widget.show()

    def _create_pagination(self, layout):
        """Создает пагинацию"""
        pagination_container = QWidget()
        pagination_container.setObjectName("PaginationContainer")
        pag_layout = QHBoxLayout(pagination_container)
        pag_layout.setContentsMargins(0, 0, 0, 0)

        # Информация о записях
        info_label = QLabel("Показано 1-10 из записей")
        info_label.setObjectName("PaginationInfo")

        # Кнопки пагинации
        self.prev_btn = QPushButton("← Предыдущая")
        self.prev_btn.setObjectName("PaginationButton")
        self.prev_btn.setFixedSize(120, 36)

        page_label = QLabel("Страница 1")
        page_label.setObjectName("PageLabel")

        self.next_btn = QPushButton("Следующая →")
        self.next_btn.setObjectName("PaginationButton")
        self.next_btn.setFixedSize(120, 36)

        pag_layout.addWidget(info_label)
        pag_layout.addStretch()
        pag_layout.addWidget(self.prev_btn)
        pag_layout.addWidget(page_label)
        pag_layout.addWidget(self.next_btn)

        layout.addWidget(pagination_container)

    def _fill_table_data(self):
        """Заполняет таблицу данными"""
        demo_data = self.config.get('demo_data', [])

        for row, data in enumerate(demo_data):
            # Чекбокс
            checkbox_container = QWidget()
            checkbox_layout = QHBoxLayout(checkbox_container)
            checkbox_layout.setContentsMargins(0, 0, 0, 0)

            checkbox = QPushButton()
            checkbox.setObjectName("RowCheckbox")
            checkbox.setCheckable(True)
            checkbox.setFixedSize(24, 24)
            checkbox.setStyleSheet("""
                QPushButton#RowCheckbox {
                    background: rgba(255, 255, 255, 0.1);
                    border: 2px solid rgba(255, 255, 255, 0.4);
                    border-radius: 6px;
                }
                QPushButton#RowCheckbox:checked {
                    background: #3B82F6;
                    border: 2px solid #3B82F6;
                }
                QPushButton#RowCheckbox:hover {
                    border: 2px solid #3B82F6;
                    background: rgba(59, 130, 246, 0.3);
                }
            """)
            checkbox.clicked.connect(lambda checked, r=row: self._handle_checkbox_click(r, checked))

            checkbox_layout.addStretch()
            checkbox_layout.addWidget(checkbox)
            checkbox_layout.addStretch()

            self.table.setCellWidget(row, 0, checkbox_container)

            # Остальные данные
            for col, value in enumerate(data, 1):
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)

                # Стиль для номеров
                if col == 1:
                    font = item.font()
                    font.setBold(True)
                    font.setPointSize(12)
                    item.setFont(font)
                    item.setForeground(QColor("#3B82F6"))

                # Стиль для премиум статуса
                if col == 7:
                    if value == "✅":
                        item.setForeground(QColor("#00FF00"))
                        font = item.font()
                        font.setBold(True)
                        font.setPointSize(18)
                        item.setFont(font)
                    else:
                        item.setForeground(QColor("#FF0000"))
                        font = item.font()
                        font.setBold(True)
                        font.setPointSize(18)
                        item.setFont(font)

                self.table.setItem(row, col, item)

        self.last_clicked_row = None

    def _toggle_all_checkboxes(self):
        """Переключает все чекбоксы"""
        master_checked = self.master_checkbox.isChecked()

        for row in range(self.table.rowCount()):
            checkbox_container = self.table.cellWidget(row, 0)
            if checkbox_container:
                checkbox = checkbox_container.findChild(QPushButton)
                if checkbox:
                    checkbox.setChecked(master_checked)

    def _handle_checkbox_click(self, row, checked):
        """Обработка клика по чекбоксу с поддержкой Shift"""
        modifiers = QApplication.keyboardModifiers()

        if modifiers == Qt.ShiftModifier and self.last_clicked_row is not None:
            start_row = min(self.last_clicked_row, row)
            end_row = max(self.last_clicked_row, row)

            for r in range(start_row, end_row + 1):
                checkbox_container = self.table.cellWidget(r, 0)
                if checkbox_container:
                    checkbox = checkbox_container.findChild(QPushButton)
                    if checkbox:
                        checkbox.setChecked(True)
        else:
            self.last_clicked_row = row

        self._update_master_checkbox()

    def _update_master_checkbox(self):
        """Обновляет состояние главного чекбокса"""
        total_rows = self.table.rowCount()
        checked_rows = 0

        for row in range(total_rows):
            checkbox_container = self.table.cellWidget(row, 0)
            if checkbox_container:
                checkbox = checkbox_container.findChild(QPushButton)
                if checkbox and checkbox.isChecked():
                    checked_rows += 1

        if checked_rows == total_rows:
            self.master_checkbox.setChecked(True)
        elif checked_rows == 0:
            self.master_checkbox.setChecked(False)

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