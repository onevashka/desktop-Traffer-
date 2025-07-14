from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QHBoxLayout, QTableWidget,
    QPushButton, QSpacerItem, QSizePolicy, QGraphicsOpacityEffect,
    QGraphicsDropShadowEffect, QHeaderView, QToolButton, QApplication,
    QStyle, QFrame, QScrollArea, QTableWidgetItem
)
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QRect, QEasingCurve, QSequentialAnimationGroup
from PySide6.QtGui import QColor, QCursor, QFont, QPalette, QLinearGradient, QBrush
import random


# УБИРАЕМ функцию insert_action_icons - она больше не нужна
# def insert_action_icons(table: QTableWidget, row: int, col: int):


class AccountManagerTab(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("AccountManagerTab")

        # Основной layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(0)  # УБИРАЕМ ВСЕ ОТСТУПЫ

        # СНАЧАЛА создаем контейнер для основного контента
        self.main_content = QWidget()
        self.main_content.setObjectName("MainContent")
        self.main_content_layout = QVBoxLayout(self.main_content)
        self.main_content_layout.setContentsMargins(0, 0, 0, 0)
        self.main_content_layout.setSpacing(0)  # УБИРАЕМ ВСЕ ОТСТУПЫ

        # Создаем анимацию загрузки
        self._create_loading_animation(layout)

        # Теперь создаем элементы интерфейса в правильном порядке
        self._create_header()
        self._create_stats_section()
        self._create_table_section()  # Таблица сразу после счетчиков
        self._create_pagination()

        # Скрываем основной контент изначально и добавляем в layout
        self.main_content.hide()
        layout.addWidget(self.main_content)

        # Запускаем анимацию загрузки
        self._start_loading_sequence()

    def _create_loading_animation(self, layout):
        # Контейнер для анимации загрузки
        self.loading_container = QWidget()
        self.loading_container.setObjectName("LoadingContainer")
        loading_layout = QVBoxLayout(self.loading_container)
        loading_layout.setContentsMargins(0, 20, 0, 20)  # Минимальные отступы загрузки
        loading_layout.setSpacing(20)

        # Индикатор загрузки
        loading_text = QLabel("Загрузка менеджера аккаунтов...")
        loading_text.setObjectName("LoadingText")
        loading_text.setAlignment(Qt.AlignCenter)
        loading_text.setStyleSheet("""
            QLabel#LoadingText {
                font-size: 18px;
                font-weight: 500;
                color: rgba(255, 255, 255, 0.8);
            }
        """)

        # Прогресс бар (имитация)
        progress_container = QWidget()
        progress_container.setFixedSize(300, 4)
        progress_container.setStyleSheet("""
            QWidget {
                background: rgba(255, 255, 255, 0.1);
                border-radius: 2px;
            }
        """)

        self.progress_bar = QWidget(progress_container)
        self.progress_bar.setObjectName("ProgressBar")
        self.progress_bar.setGeometry(0, 0, 0, 4)
        self.progress_bar.setStyleSheet("""
            QWidget#ProgressBar {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3B82F6, stop:1 #8B5CF6);
                border-radius: 2px;
            }
        """)

        loading_layout.addStretch()
        loading_layout.addWidget(loading_text, 0, Qt.AlignCenter)
        loading_layout.addWidget(progress_container, 0, Qt.AlignCenter)
        loading_layout.addStretch()

        layout.addWidget(self.loading_container)

    def _create_header(self):
        # Только заголовок по центру - БЕЗ кнопки
        title_container = QWidget()
        title_layout = QHBoxLayout(title_container)
        title_layout.setContentsMargins(0, 0, 0, 10)  # Маленький отступ снизу

        title = QLabel("Менеджер Аккаунтов")
        title.setObjectName("MainTitle")
        title.setAlignment(Qt.AlignCenter)

        title_layout.addStretch()
        title_layout.addWidget(title)
        title_layout.addStretch()

        self.main_content_layout.addWidget(title_container)

    def _create_stats_section(self):
        stats_container = QWidget()
        stats_container.setObjectName("StatsContainer")
        stats_layout = QHBoxLayout(stats_container)
        stats_layout.setContentsMargins(0, 5, 0, 15)  # Небольшие отступы
        stats_layout.setSpacing(20)  # Больше пространства между счетчиками

        # Статистики с правильными данными - РАСШИРЯЕМ по всей ширине
        stats_data = [
            ("Всего аккаунтов", "153", "#3B82F6"),
            ("Мертвых", "144", "#EF4444"),
            ("На проверке", "9", "#F59E0B"),
            ("Готовых к работе", "0", "#10B981")
        ]

        self.stat_boxes = []
        for i, (title, value, color) in enumerate(stats_data):
            box = self._build_stat_box(title, value, color)
            self.stat_boxes.append(box)
            stats_layout.addWidget(box)

        # УБИРАЕМ addStretch() чтобы счетчики растянулись по всей ширине
        self.main_content_layout.addWidget(stats_container)

    def _build_stat_box(self, title, value, color):
        box = QWidget()
        box.setObjectName("StatBox")
        # РАСШИРЯЕМ счетчики - убираем фиксированный размер
        box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        box.setFixedHeight(90)  # Только фиксируем высоту

        # Layout
        layout = QHBoxLayout(box)
        layout.setContentsMargins(20, 20, 20, 20)  # Больше отступов для красоты
        layout.setSpacing(15)

        # Левая часть - индикатор
        indicator = QWidget()
        indicator.setObjectName("StatIndicator")
        indicator.setFixedSize(5, 50)  # Чуть шире индикатор
        indicator.setStyleSheet(f"""
            QWidget#StatIndicator {{
                background: {color};
                border-radius: 3px;
            }}
        """)

        # Правая часть - текст
        text_container = QWidget()
        text_layout = QVBoxLayout(text_container)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(5)

        # Значение
        value_label = QLabel(value)
        value_label.setObjectName("StatValue")
        value_label.setStyleSheet(f"""
            QLabel#StatValue {{
                font-size: 26px;
                font-weight: 700;
                color: {color};
            }}
        """)

        # Заголовок
        title_label = QLabel(title)
        title_label.setObjectName("StatTitle")
        title_label.setStyleSheet("""
            QLabel#StatTitle {
                font-size: 13px;
                font-weight: 500;
                color: rgba(255, 255, 255, 0.8);
            }
        """)

        text_layout.addWidget(value_label)
        text_layout.addWidget(title_label)
        text_layout.addStretch()

        layout.addWidget(indicator)
        layout.addWidget(text_container)

        return box

    def _create_table_section(self):
        # Кнопки массовых действий ПЕРЕД таблицей
        actions_container = QWidget()
        actions_container.setObjectName("ActionsContainer")
        actions_layout = QHBoxLayout(actions_container)
        actions_layout.setContentsMargins(0, 5, 0, 10)
        actions_layout.setSpacing(10)

        # Убираем кнопку "Выбрать все" - теперь она в заголовке
        section_title = QLabel("📋 Список аккаунтов")
        section_title.setObjectName("SectionTitle")
        section_title.setStyleSheet("""
            QLabel#SectionTitle {
                font-size: 16px;
                font-weight: 600;
                color: rgba(255, 255, 255, 0.9);
            }
        """)

        # Кнопки массовых действий БЕЗ "Выбрать все"
        delete_btn = QPushButton("🗑️ Удалить")
        delete_btn.setObjectName("ActionButton")
        delete_btn.setFixedSize(100, 36)

        update_btn = QPushButton("🔄 Обновить")
        update_btn.setObjectName("ActionButton")
        update_btn.setFixedSize(110, 36)

        move_btn = QPushButton("📦 Переместить")
        move_btn.setObjectName("ActionButton")
        move_btn.setFixedSize(130, 36)

        archive_btn = QPushButton("📁 Архивировать")
        archive_btn.setObjectName("ActionButton")
        archive_btn.setFixedSize(140, 36)

        # Кнопка добавления справа
        add_btn = QPushButton("+ Добавить аккаунт")
        add_btn.setObjectName("AddButton")
        add_btn.setFixedSize(160, 36)

        actions_layout.addWidget(section_title)
        actions_layout.addWidget(delete_btn)
        actions_layout.addWidget(update_btn)
        actions_layout.addWidget(move_btn)
        actions_layout.addWidget(archive_btn)
        actions_layout.addStretch()
        actions_layout.addWidget(add_btn)

        self.main_content_layout.addWidget(actions_container)

        # Теперь сама таблица
        table_container = QWidget()
        table_container.setObjectName("TableContainer")
        table_layout = QVBoxLayout(table_container)
        table_layout.setContentsMargins(0, 0, 0, 0)

        # Таблица С НУМЕРАЦИЕЙ И ЧЕКБОКСАМИ - 8 колонок
        self.table = QTableWidget(10, 8)  # Добавляем колонку для чекбоксов
        self.table.setObjectName("ModernTable")
        self.table.setHorizontalHeaderLabels([
            "",  # Пустой заголовок - добавим чекбокс программно
            "#",  # Нумерация
            "Название аккаунта",
            "🌍 Гео",
            "📅 Дней создан",
            "⏰ Последний онлайн",
            "👤 Имя",
            "💎 Премиум"
        ])
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)

        # Добавляем главный чекбокс в заголовок
        self._create_header_checkbox()

        # Увеличиваем высоту строк
        self.table.verticalHeader().setDefaultSectionSize(60)

        # Заполнение данными
        self._fill_demo_data()

        # Настройка колонок
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)  # Чекбоксы - фиксированный
        header.setSectionResizeMode(1, QHeaderView.Fixed)  # Номер - фиксированный
        header.setSectionResizeMode(2, QHeaderView.Stretch)  # Название аккаунта
        header.setSectionResizeMode(3, QHeaderView.Stretch)  # Гео
        header.setSectionResizeMode(4, QHeaderView.Stretch)  # Дней создан
        header.setSectionResizeMode(5, QHeaderView.Stretch)  # Последний онлайн
        header.setSectionResizeMode(6, QHeaderView.Stretch)  # Имя
        header.setSectionResizeMode(7, QHeaderView.Stretch)  # Премиум

        # Фиксированные размеры для служебных колонок
        self.table.setColumnWidth(0, 50)  # Чекбоксы
        self.table.setColumnWidth(1, 60)  # Номера

        table_layout.addWidget(self.table)
        self.main_content_layout.addWidget(table_container)
        """Создаем главный чекбокс в заголовке таблицы"""
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(0)

        # Главный чекбокс для выбора всех
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

        # Устанавливаем виджет в заголовок первой колонки
        self.table.horizontalHeader().sectionResized.connect(
            lambda index, oldSize, newSize: self._update_header_checkbox_position()
        )

        # Добавляем виджет в заголовок после создания таблицы
        QTimer.singleShot(100, lambda: self._place_header_checkbox(header_widget))

    def _place_header_checkbox(self, widget):
        """Размещаем чекбокс в заголовке"""
        # Получаем позицию первой колонки
        header = self.table.horizontalHeader()
        x = header.sectionPosition(0)
        width = header.sectionSize(0)

        widget.setParent(header)
        widget.setGeometry(x, 0, width, header.height())
        widget.show()

    def _update_header_checkbox_position(self):
        """Обновляем позицию чекбокса при изменении размеров"""
        # Эта функция будет вызываться при изменении размеров колонок
        pass

    def _fill_demo_data(self):
        demo_data = [
            ["1", "@telegram_user_1", "RU", "15", "5 мин назад", "Александр К.", "✅"],
            ["2", "@john_smith_usa", "US", "32", "1 час назад", "John Smith", "❌"],
            ["3", "@emma_wilson_uk", "UK", "8", "2 часа назад", "Emma Wilson", "✅"],
            ["4", "@hans_mueller_de", "DE", "45", "3 часа назад", "Hans Mueller", "❌"],
            ["5", "@marie_dubois_fr", "FR", "22", "5 часов назад", "Marie Dubois", "✅"],
            ["6", "@tanaka_hiroshi", "JP", "67", "1 день назад", "Tanaka Hiroshi", "❌"],
            ["7", "@li_wei_china", "CN", "11", "2 дня назад", "Li Wei", "✅"],
            ["8", "@raj_patel_india", "IN", "29", "3 дня назад", "Raj Patel", "❌"],
            ["9", "@carlos_silva_br", "BR", "88", "1 неделя назад", "Carlos Silva", "✅"],
            ["10", "@sarah_johnson", "AU", "156", "2 недели назад", "Sarah Johnson", "❌"],
        ]

        for row, data in enumerate(demo_data):
            # Создаем контейнер для центрирования чекбокса
            checkbox_container = QWidget()
            checkbox_layout = QHBoxLayout(checkbox_container)
            checkbox_layout.setContentsMargins(0, 0, 0, 0)
            checkbox_layout.setSpacing(0)

            # Создаем ОДИНАКОВЫЕ чекбоксы для каждой строки
            checkbox = QPushButton()
            checkbox.setObjectName("RowCheckbox")
            checkbox.setCheckable(True)
            checkbox.setFixedSize(24, 24)  # Такой же размер как главный
            checkbox.setProperty("row", row)  # Сохраняем номер строки для shift-выбора
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

            # Центрируем чекбокс в контейнере
            checkbox_layout.addStretch()
            checkbox_layout.addWidget(checkbox)
            checkbox_layout.addStretch()

            self.table.setCellWidget(row, 0, checkbox_container)

            # Заполняем остальные колонки (сдвигаем на +1)
            for col, value in enumerate(data, 1):  # Начинаем с колонки 1
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)

                # Стиль для колонки номеров (теперь колонка 1)
                if col == 1:  # Колонка номеров
                    font = item.font()
                    font.setBold(True)
                    font.setPointSize(12)
                    item.setFont(font)
                    item.setForeground(QColor("#3B82F6"))  # Синий цвет для номеров

                # Цветовая индикация премиум статуса - теперь колонка 7
                if col == 7:  # Колонка премиум (сдвинулась на +1)
                    if value == "✅":
                        item.setForeground(QColor("#00FF00"))  # ЯРКО-ЗЕЛЕНЫЙ
                        # Делаем шрифт ОГРОМНЫМ
                        font = item.font()
                        font.setBold(True)
                        font.setPointSize(18)  # ОЧЕНЬ БОЛЬШОЙ размер
                        item.setFont(font)
                    else:
                        item.setForeground(QColor("#FF0000"))  # ЯРКО-КРАСНЫЙ
                        # Делаем шрифт ОГРОМНЫМ
                        font = item.font()
                        font.setBold(True)
                        font.setPointSize(18)  # ОЧЕНЬ БОЛЬШОЙ размер
                        item.setFont(font)

                self.table.setItem(row, col, item)

        # Инициализируем переменные для shift-выбора
        self.last_clicked_row = None

    def _create_pagination(self):
        pagination_container = QWidget()
        pagination_container.setObjectName("PaginationContainer")
        pag_layout = QHBoxLayout(pagination_container)
        pag_layout.setContentsMargins(0, 0, 0, 0)  # УБИРАЕМ ВСЕ ОТСТУПЫ

        # Информация о записях
        info_label = QLabel("Показано 1-10 из 153 записей")
        info_label.setObjectName("PaginationInfo")

        pag_layout.addWidget(info_label)
        pag_layout.addStretch()

        # Кнопки пагинации
        self.prev_btn = QPushButton("← Предыдущая")
        self.prev_btn.setObjectName("PaginationButton")
        self.prev_btn.setFixedSize(120, 36)

        page_label = QLabel("Страница 1 из 16")
        page_label.setObjectName("PageLabel")

        self.next_btn = QPushButton("Следующая →")
        self.next_btn.setObjectName("PaginationButton")
        self.next_btn.setFixedSize(120, 36)

        pag_layout.addWidget(self.prev_btn)
        pag_layout.addWidget(page_label)
        pag_layout.addWidget(self.next_btn)

        self.main_content_layout.addWidget(pagination_container)

    def _create_header_checkbox(self):
        """Создаем главный чекбокс в заголовке таблицы"""
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(0)

        # Главный чекбокс для выбора всех
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

        # Устанавливаем виджет в заголовок первой колонки
        self.table.horizontalHeader().sectionResized.connect(
            lambda index, oldSize, newSize: self._update_header_checkbox_position()
        )

        # Добавляем виджет в заголовок после создания таблицы
        QTimer.singleShot(100, lambda: self._place_header_checkbox(header_widget))

    def _place_header_checkbox(self, widget):
        """Размещаем чекбокс в заголовке"""
        # Получаем позицию первой колонки
        header = self.table.horizontalHeader()
        x = header.sectionPosition(0)
        width = header.sectionSize(0)

        widget.setParent(header)
        widget.setGeometry(x, 0, width, header.height())
        widget.show()

    def _update_header_checkbox_position(self):
        """Обновляем позицию чекбокса при изменении размеров"""
        # Эта функция будет вызываться при изменении размеров колонок
        pass

    def _toggle_all_checkboxes(self):
        """Переключаем все чекбоксы в строках"""
        master_checked = self.master_checkbox.isChecked()

        for row in range(self.table.rowCount()):
            checkbox_container = self.table.cellWidget(row, 0)
            if checkbox_container:
                # Ищем чекбокс внутри контейнера
                checkbox = checkbox_container.findChild(QPushButton)
                if checkbox:
                    checkbox.setChecked(master_checked)

    def _handle_checkbox_click(self, row, checked):
        """Обработка клика по чекбоксу с поддержкой Shift-выбора"""
        # Получаем модификаторы клавиатуры
        modifiers = QApplication.keyboardModifiers()

        if modifiers == Qt.ShiftModifier and self.last_clicked_row is not None:
            # Shift-выбор диапазона
            start_row = min(self.last_clicked_row, row)
            end_row = max(self.last_clicked_row, row)

            # Выбираем все строки в диапазоне
            for r in range(start_row, end_row + 1):
                checkbox_container = self.table.cellWidget(r, 0)
                if checkbox_container:
                    # Ищем чекбокс внутри контейнера
                    checkbox = checkbox_container.findChild(QPushButton)
                    if checkbox:
                        checkbox.setChecked(True)
        else:
            # Обычный клик - запоминаем строку
            self.last_clicked_row = row

        # Обновляем состояние главного чекбокса
        self._update_master_checkbox()

    def _update_master_checkbox(self):
        """Обновляем состояние главного чекбокса в зависимости от строк"""
        total_rows = self.table.rowCount()
        checked_rows = 0

        for row in range(total_rows):
            checkbox_container = self.table.cellWidget(row, 0)
            if checkbox_container:
                # Ищем чекбокс внутри контейнера
                checkbox = checkbox_container.findChild(QPushButton)
                if checkbox and checkbox.isChecked():
                    checked_rows += 1

        # Если все выбраны - ставим галочку, если никто - убираем
        if checked_rows == total_rows:
            self.master_checkbox.setChecked(True)
        elif checked_rows == 0:
            self.master_checkbox.setChecked(False)
        # Если частично выбраны - можно оставить как есть

    def _select_all_accounts(self):
        """Функция для выбора/снятия выбора всех аккаунтов"""
        # Проверяем, есть ли выбранные чекбоксы
        selected_count = 0
        total_count = self.table.rowCount()

        for row in range(total_count):
            checkbox = self.table.cellWidget(row, 0)
            if checkbox and checkbox.isChecked():
                selected_count += 1

        # Если все выбраны - снимаем выбор, иначе выбираем все
        select_all = selected_count < total_count

        for row in range(total_count):
            checkbox = self.table.cellWidget(row, 0)
            if checkbox:
                checkbox.setChecked(select_all)

        # Обновляем текст кнопки
        sender = self.sender()
        if select_all:
            sender.setText("☑️ Снять все")
        else:
            sender.setText("☑️ Выбрать все")

    def _start_loading_sequence(self):
        # Анимация прогресс бара
        self.progress_animation = QPropertyAnimation(self.progress_bar, b"geometry")
        self.progress_animation.setDuration(2000)
        self.progress_animation.setStartValue(QRect(0, 0, 0, 4))
        self.progress_animation.setEndValue(QRect(0, 0, 300, 4))
        self.progress_animation.setEasingCurve(QEasingCurve.OutCubic)

        # После завершения загрузки показываем контент
        self.progress_animation.finished.connect(self._show_main_content)

        # Запускаем анимацию через небольшую задержку
        QTimer.singleShot(500, self.progress_animation.start)

    def _show_main_content(self):
        # Скрываем загрузку
        self.loading_container.hide()

        # Показываем основной контент с анимацией
        self.main_content.show()

        # Анимация появления контента
        effect = QGraphicsOpacityEffect(self.main_content)
        self.main_content.setGraphicsEffect(effect)

        self.content_animation = QPropertyAnimation(effect, b"opacity")
        self.content_animation.setDuration(800)
        self.content_animation.setStartValue(0.0)
        self.content_animation.setEndValue(1.0)
        self.content_animation.setEasingCurve(QEasingCurve.OutCubic)
        self.content_animation.start()

        # НЕ запускаем анимацию появления статистик - они просто остаются видимыми
        # for i, box in enumerate(self.stat_boxes):
        #     QTimer.singleShot(i * 100 + 300, lambda b=box: self._animate_stat_box(b))

    def _animate_stat_box(self, box):
        # Анимация появления статистики БЕЗ изменения graphicsEffect
        # Просто показываем box без дополнительных эффектов
        box.show()

        # Создаем временную анимацию масштабирования
        box.setProperty("scale", 0.8)

        # Анимация масштабирования
        self.scale_animation = QPropertyAnimation(box, b"geometry")
        current_geo = box.geometry()

        # Начальная позиция (чуть меньше)
        start_geo = QRect(
            current_geo.x() + 10,
            current_geo.y() + 5,
            current_geo.width() - 20,
            current_geo.height() - 10
        )

        self.scale_animation.setDuration(300)
        self.scale_animation.setStartValue(start_geo)
        self.scale_animation.setEndValue(current_geo)
        self.scale_animation.setEasingCurve(QEasingCurve.OutBack)
        self.scale_animation.start()