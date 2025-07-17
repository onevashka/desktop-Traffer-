"""
Красивое модальное окно для перемещения аккаунтов между папками
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QWidget, QFrame, QGraphicsOpacityEffect,
    QGraphicsDropShadowEffect, QApplication, QComboBox
)
from PySide6.QtCore import (
    Qt, QPropertyAnimation, QEasingCurve, QTimer, QRect,
    QParallelAnimationGroup, Signal
)
from PySide6.QtGui import QFont, QColor, QPalette, QPixmap, QPainter
from typing import List, Dict, Optional


class MoveAccountsDialog(QDialog):
    """Красивое модальное окно для перемещения аккаунтов"""

    # Результаты диалога
    ACCEPTED = 1
    REJECTED = 0

    def __init__(self, accounts_info: List[Dict], destinations: List[Dict],
                 current_category: str, parent=None):
        super().__init__(parent)

        self.accounts_info = accounts_info
        self.destinations = destinations
        self.current_category = current_category
        self.result_value = self.REJECTED
        self.selected_destination = None

        # Настройки окна
        self.setWindowTitle("Перемещение аккаунтов")
        self.setModal(True)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # Размеры
        self.setFixedSize(650, 550)

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
        title_label = QLabel("Перемещение аккаунтов")
        title_label.setObjectName("DialogTitle")
        title_label.setWordWrap(True)

        header_layout.addWidget(icon_label)
        header_layout.addWidget(title_label, 1)

        # Основное сообщение
        count = len(self.accounts_info)
        if count == 1:
            message = "Выберите папку назначения для перемещения аккаунта:"
        else:
            message = f"Выберите папку назначения для перемещения {count} аккаунт(ов):"

        message_label = QLabel(message)
        message_label.setObjectName("DialogMessage")
        message_label.setWordWrap(True)

        # Выпадающий список назначений
        destination_layout = self._create_destination_selector()

        # Список аккаунтов
        accounts_container = self._create_accounts_list()

        # Предупреждение о дубликатах
        warning_label = QLabel("ℹ️ Аккаунты с дубликатами имен будут пропущены при перемещении")
        warning_label.setObjectName("InfoLabel")
        warning_label.setWordWrap(True)

        # Кнопки
        buttons_layout = self._create_buttons()

        # Сборка layout
        content_layout.addLayout(header_layout)
        content_layout.addWidget(message_label)
        content_layout.addLayout(destination_layout)
        content_layout.addWidget(accounts_container, 1)
        content_layout.addWidget(warning_label)
        content_layout.addLayout(buttons_layout)

        main_layout.addWidget(self.content_container)

        # Тень
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(30)
        shadow.setXOffset(0)
        shadow.setYOffset(10)
        shadow.setColor(QColor(0, 0, 0, 120))
        self.content_container.setGraphicsEffect(shadow)

    def _create_destination_selector(self) -> QVBoxLayout:
        """Создает селектор папки назначения"""
        layout = QVBoxLayout()
        layout.setSpacing(10)

        # Подпись
        label = QLabel("Папка назначения:")
        label.setObjectName("SelectorLabel")

        # Выпадающий список
        self.destination_combo = QComboBox()
        self.destination_combo.setObjectName("DestinationCombo")
        self.destination_combo.setFixedHeight(40)

        # Добавляем варианты
        self.destination_combo.addItem("Выберите папку назначения...", None)

        for dest in self.destinations:
            display_name = dest['display_name']
            self.destination_combo.addItem(display_name, dest)

        # Подключаем обработчик изменения
        self.destination_combo.currentIndexChanged.connect(self._on_destination_changed)

        layout.addWidget(label)
        layout.addWidget(self.destination_combo)

        return layout

    def _create_accounts_list(self) -> QWidget:
        """Создает список аккаунтов"""
        container = QFrame()
        container.setObjectName("AccountsContainer")

        # Подпись
        list_label = QLabel(f"Аккаунты для перемещения ({len(self.accounts_info)}):")
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

        # Если аккаунтов много, показываем только первые 15
        if len(self.accounts_info) > 15:
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
        if index >= 15:  # Показываем только первые 15
            return QWidget()

        item = QFrame()
        item.setObjectName("AccountItem")

        layout = QHBoxLayout(item)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(10)

        # Иконка перемещения
        icon = QLabel("📤")
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

        # Текущий статус
        current_status = self._get_status_display(account.get('status', 'unknown'))
        status_label = QLabel(f"Из: {current_status}")
        status_label.setObjectName("CurrentStatus")

        layout.addWidget(icon)
        layout.addLayout(info_layout, 1)
        layout.addWidget(status_label)

        return item

    def _create_more_indicator(self) -> QWidget:
        """Создает индикатор "еще N аккаунтов"""
        remaining = len(self.accounts_info) - 15

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
        self.confirm_button = QPushButton("Переместить")
        self.confirm_button.setObjectName("ConfirmButton")
        self.confirm_button.setFixedSize(140, 44)
        self.confirm_button.setEnabled(False)  # Изначально отключена
        self.confirm_button.clicked.connect(self._on_confirm)

        layout.addStretch()
        layout.addWidget(self.cancel_button)
        layout.addWidget(self.confirm_button)

        return layout

    def _get_status_display(self, status: str) -> str:
        """Получает отображаемый статус"""
        status_map = {
            "active": "✅ Активные",
            "dead": "❌ Мертвые",
            "frozen": "🧊 Замороженные",
            "invalid": "⚠️ Неверный формат",
            "registration": "📝 Регистрация",
            "ready_tdata": "📁 TData",
            "ready_sessions": "📄 Session+JSON",
            "middle": "🟡 Средние"
        }
        return status_map.get(status, status)

    def _on_destination_changed(self, index: int):
        """Обработка изменения выбранного назначения"""
        if index > 0:  # Не первый элемент (заглушка)
            self.selected_destination = self.destination_combo.itemData(index)
            self.confirm_button.setEnabled(True)
        else:
            self.selected_destination = None
            self.confirm_button.setEnabled(False)

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

            /* Подпись селектора */
            QLabel#SelectorLabel {
                font-size: 14px;
                font-weight: 500;
                color: rgba(255, 255, 255, 0.9);
                margin: 0;
            }

            /* Выпадающий список */
            QComboBox#DestinationCombo {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 14px;
                color: rgba(255, 255, 255, 0.9);
                selection-background-color: rgba(59, 130, 246, 0.3);
            }

            QComboBox#DestinationCombo:hover {
                border-color: rgba(59, 130, 246, 0.5);
                background: rgba(255, 255, 255, 0.08);
            }

            QComboBox#DestinationCombo:focus {
                border-color: #3B82F6;
                background: rgba(255, 255, 255, 0.1);
            }

            QComboBox#DestinationCombo::drop-down {
                border: none;
                padding-right: 8px;
            }

            QComboBox#DestinationCombo::down-arrow {
                image: none;
                border: none;
                width: 0;
                height: 0;
            }

            QComboBox#DestinationCombo QAbstractItemView {
                background: rgba(30, 30, 30, 0.95);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                selection-background-color: rgba(59, 130, 246, 0.3);
                color: rgba(255, 255, 255, 0.9);
                padding: 4px;
            }

            QComboBox#DestinationCombo QAbstractItemView::item {
                padding: 8px 12px;
                border-radius: 4px;
                margin: 1px;
            }

            QComboBox#DestinationCombo QAbstractItemView::item:hover {
                background: rgba(59, 130, 246, 0.2);
            }

            QComboBox#DestinationCombo QAbstractItemView::item:selected {
                background: rgba(59, 130, 246, 0.4);
            }

            /* Подпись списка */
            QLabel#ListLabel {
                font-size: 13px;
                font-weight: 500;
                color: rgba(255, 255, 255, 0.8);
                margin: 0;
            }

            /* Контейнер аккаунтов */
            QFrame#AccountsContainer {
                background: rgba(255, 255, 255, 0.02);
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 8px;
                padding: 8px;
            }

            /* Скролл область */
            QScrollArea#AccountsScroll {
                background: transparent;
                border: none;
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

            /* Иконка аккаунта */
            QLabel#AccountIcon {
                font-size: 16px;
                color: rgba(255, 255, 255, 0.6);
            }

            /* Имя аккаунта */
            QLabel#AccountName {
                font-size: 13px;
                font-weight: 600;
                color: rgba(255, 255, 255, 0.9);
                margin: 0;
            }

            /* Детали аккаунта */
            QLabel#AccountDetails {
                font-size: 11px;
                color: rgba(255, 255, 255, 0.6);
                margin: 0;
            }

            /* Текущий статус */
            QLabel#CurrentStatus {
                font-size: 11px;
                color: rgba(255, 255, 255, 0.7);
                background: rgba(255, 255, 255, 0.05);
                padding: 4px 8px;
                border-radius: 4px;
                margin: 0;
            }

            /* Информационная подпись */
            QLabel#InfoLabel {
                font-size: 12px;
                font-weight: 400;
                color: rgba(59, 130, 246, 0.8);
                background: rgba(59, 130, 246, 0.05);
                border: 1px solid rgba(59, 130, 246, 0.2);
                border-radius: 6px;
                padding: 10px;
                margin: 0;
            }

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

            QPushButton#CancelButton:pressed {
                background: rgba(255, 255, 255, 0.15);
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

            QPushButton#ConfirmButton:hover:enabled {
                background: #047857;
                border-color: #047857;
            }

            QPushButton#ConfirmButton:pressed:enabled {
                background: #065f46;
            }

            QPushButton#ConfirmButton:disabled {
                background: rgba(255, 255, 255, 0.05);
                border-color: rgba(255, 255, 255, 0.05);
                color: rgba(255, 255, 255, 0.3);
            }

            /* Скроллбар */
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
                background: rgba(255, 255, 255, 0.3);
            }

            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
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
        self.result_value = self.ACCEPTED
        self._animate_out(self.close)

    def exec(self) -> int:
        """Показывает диалог модально"""
        super().exec()
        return self.result_value

    def get_selected_destination(self) -> Optional[Dict]:
        """Возвращает выбранное назначение"""
        return self.selected_destination

    def keyPressEvent(self, event):
        """Обработка клавиш"""
        if event.key() == Qt.Key_Escape:
            self._on_cancel()
        elif event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            if self.confirm_button.isEnabled():
                self._on_confirm()
        else:
            super().keyPressEvent(event)


def show_move_accounts_dialog(parent, accounts_info: List[Dict],
                              destinations: List[Dict], current_category: str) -> Optional[Dict]:
    """
    Удобная функция для показа диалога перемещения аккаунтов

    Returns:
        Словарь с информацией о назначении или None если отменили
    """
    dialog = MoveAccountsDialog(accounts_info, destinations, current_category, parent)
    result = dialog.exec()

    if result == MoveAccountsDialog.ACCEPTED:
        return dialog.get_selected_destination()
    else:
        return None