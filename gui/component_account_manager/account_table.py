# TeleCRM/gui/components/account_table.py
"""
Компонент таблицы аккаунтов
"""
from typing import List
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QHeaderView, QApplication, QGraphicsOpacityEffect
)
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QColor

from gui.handlers import TableActionHandler



class AccountTableWidget(QWidget):
    """Виджет таблицы аккаунтов"""

    def __init__(self, config):
        """
        config: словарь с настройками
        {
            'title': 'Заголовок таблицы',
            'add_button_text': 'Текст кнопки добавления',
            'demo_data': [[...], [...]]  # Данные для таблицы
            'category': 'traffic' или 'sales',
            'current_status': 'active' или другой статус  # НОВОЕ
        }
        """
        super().__init__()
        self.setObjectName("AccountTableWidget")
        self.config = config

        # НОВОЕ: Отслеживаем текущий статус (папку)
        self.current_status = config.get('current_status', 'active')
        self.category = config.get('category', 'traffic')

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

        # Заголовок секции - ОБНОВЛЕНО
        self.section_title = QLabel()
        self.section_title.setObjectName("SectionTitle")
        self.section_title.setStyleSheet("""
            QLabel#SectionTitle {
                font-size: 16px;
                font-weight: 600;
                color: rgba(255, 255, 255, 0.9);
            }
        """)
        self._update_section_title()  # Устанавливаем правильный заголовок

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

        actions_layout.addWidget(self.section_title)
        actions_layout.addWidget(self.delete_btn)
        actions_layout.addWidget(self.update_btn)
        actions_layout.addWidget(self.move_btn)
        actions_layout.addWidget(self.archive_btn)
        actions_layout.addStretch()
        actions_layout.addWidget(self.add_btn)

        layout.addWidget(actions_container)

        # Подключаем обработчики
        self.action_handler = TableActionHandler(self)
        self.delete_btn.clicked.connect(self.action_handler.handle_delete_action)
        self.update_btn.clicked.connect(self.action_handler.handle_refresh_action)
        self.move_btn.clicked.connect(self.action_handler.handle_move_action)

    def get_selected_account_names(self) -> List[str]:
        """Возвращает список имен выбранных аккаунтов"""
        selected_rows = self.get_selected_rows()
        account_names = []

        for row in selected_rows:
            # Берем имя из колонки "📱 Аккаунт" (индекс 2)
            item = self.table.item(row, 2)
            if item:
                account_name = item.text()
                account_names.append(account_name)

        return account_names

    def get_table_category(self) -> str:
        """Определяет категорию таблицы по заголовку"""
        if hasattr(self.table, 'category'):
            return self.table.category

        # Fallback - старый способ
        title = self.table.config.get('title', '').lower()
        if 'трафик' in title:
            return 'traffic'
        elif 'продаж' in title:
            return 'sales'
        return 'traffic'  # По умолчанию

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

    def get_current_status(self) -> str:
        """Получает текущий статус (папку) таблицы"""
        if hasattr(self.table, 'get_current_status'):
            return self.table.get_current_status()
        return self.table.config.get('current_status', 'active')

    def get_category(self) -> str:
        """Возвращает категорию"""
        return self.category

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

    def refresh_data(self):
        """Обновление данных таблицы для текущей папки"""
        try:
            from src.accounts.manager import get_table_data

            # Получаем данные для текущей папки
            new_data = get_table_data(self.category, self.current_status, limit=50)
            self.config['demo_data'] = new_data

            # Обновляем таблицу
            if hasattr(self, 'update_table_data'):
                self.update_table_data(new_data)
            elif hasattr(self, '_fill_table_data'):
                self._fill_table_data()

        except Exception as e:
            print(f"❌ Ошибка refresh_data: {e}")

    def set_current_status(self, status: str):
        """Устанавливает текущий статус (папку) для отображения"""
        self.current_status = status
        self.config['current_status'] = status

        # Обновляем заголовок
        self._update_section_title()

        # Обновляем данные таблицы
        self.refresh_data()

    def _update_section_title(self):
        """Обновляет заголовок секции в зависимости от текущей папки"""
        if hasattr(self, 'section_title'):
            from src.accounts.manager import get_status_display_name
            folder_name = get_status_display_name(self.category, self.current_status)

            # Иконки для разных категорий
            if self.category == "traffic":
                icon = "🚀"
            elif self.category == "sales":
                icon = "💰"
            else:
                icon = "📋"

            self.section_title.setText(f"{icon} {folder_name}")

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

    def update_table_data(self, new_data):
        """Обновляет данные в таблице"""
        from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QTableWidgetItem
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QColor

        # Очищаем текущие данные
        self.table.clearContents()
        self.table.setRowCount(len(new_data))

        if len(new_data) == 0:
            # Если нет данных, показываем заглушку
            placeholder_item = QTableWidgetItem("Нет аккаунтов для отображения")
            placeholder_item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
            self.table.setItem(0, 1, placeholder_item)
            self.table.setSpan(0, 1, 1, 7)  # Объединяем ячейки
            return

        # Заполняем новыми данными
        for row, data in enumerate(new_data):
            # Чекбокс (такой же как в оригинальном методе)
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

                # Стиль для статуса (колонка 5 - это "📊 Статус")
                if col == 5:
                    status_text = str(value)
                    if "Активный" in status_text or "готов" in status_text:
                        item.setForeground(QColor("#10B981"))  # Зеленый
                    elif "Мертвый" in status_text:
                        item.setForeground(QColor("#EF4444"))  # Красный
                    elif "Заморожен" in status_text:
                        item.setForeground(QColor("#F59E0B"))  # Оранжевый
                    elif "Неверный" in status_text:
                        item.setForeground(QColor("#6B7280"))  # Серый
                    else:
                        item.setForeground(QColor("#8B5CF6"))  # Фиолетовый

                # Стиль для премиум статуса (последняя колонка)
                if col == len(data):
                    if value == "✅":
                        item.setForeground(QColor("#00FF00"))
                        font = item.font()
                        font.setBold(True)
                        font.setPointSize(18)
                        item.setFont(font)
                    elif value == "❌":
                        item.setForeground(QColor("#FF0000"))
                        font = item.font()
                        font.setBold(True)
                        font.setPointSize(18)
                        item.setFont(font)

                self.table.setItem(row, col, item)

        # Сбрасываем главный чекбокс
        if hasattr(self, 'master_checkbox'):
            self.master_checkbox.setChecked(False)

        # Обновляем last_clicked_row
        self.last_clicked_row = None