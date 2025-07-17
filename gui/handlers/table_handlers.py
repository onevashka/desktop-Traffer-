# gui/handlers/table_handlers.py - ИСПРАВЛЕННАЯ ВЕРСИЯ
"""
Обработчики действий с таблицами аккаунтов - с красивыми модальными окнами
"""

from typing import List, Dict, Optional
from PySide6.QtWidgets import QMessageBox
from PySide6.QtCore import QTimer
from loguru import logger

# Импортируем систему уведомлений
from gui.notifications import show_success, show_error, show_warning, show_info

# Импортируем красивые модальные окна
from gui.dialogs.custom_confirm_dialog import show_delete_confirmation


class TableActionHandler:
    """Обработчик действий с таблицей аккаунтов"""

    def __init__(self, table_widget):
        """
        table_widget: Ссылка на AccountTableWidget
        """
        self.table = table_widget

    def handle_delete_action(self):
        """Обрабатывает удаление выбранных аккаунтов"""
        try:
            # Получаем выбранные аккаунты
            selected_accounts = self.table.get_selected_account_names()
            category = self.get_table_category()

            if not selected_accounts:
                show_info(
                    "Удаление аккаунтов",
                    "Выберите аккаунты для удаления"
                )
                return

            if not category:
                show_error(
                    "Ошибка",
                    "Не удалось определить категорию аккаунтов"
                )
                return

            # Получаем менеджер аккаунтов
            from src.accounts.manager import _account_manager

            if not _account_manager:
                show_error(
                    "Ошибка",
                    "Менеджер аккаунтов не инициализирован"
                )
                return

            # Получаем информацию об аккаунтах для удаления
            accounts_info = _account_manager.get_account_info_for_deletion(selected_accounts, category)

            # Показываем красивое модальное окно
            if self._show_beautiful_confirmation(accounts_info):
                self._perform_deletion(selected_accounts, category)

        except Exception as e:
            logger.error(f"❌ Ошибка обработки удаления: {e}")
            show_error(
                "Критическая ошибка",
                f"Ошибка при удалении: {e}"
            )

    def _show_beautiful_confirmation(self, accounts_info: List[dict]) -> bool:
        """Показывает красивое модальное окно подтверждения"""
        if not accounts_info:
            show_warning("Ошибка", "Аккаунты не найдены")
            return False

        # Формируем заголовок и сообщение
        count = len(accounts_info)
        title = f"Подтверждение удаления"

        if count == 1:
            message = f"Вы действительно хотите удалить этот аккаунт?"
        else:
            message = f"Вы действительно хотите удалить {count} аккаунт(ов)?"

        # Находим родительское окно
        parent_window = self.table
        while parent_window.parent():
            parent_window = parent_window.parent()

        # Показываем красивое модальное окно
        return show_delete_confirmation(
            parent=parent_window,
            title=title,
            message=message,
            accounts_info=accounts_info
        )

    def _perform_deletion(self, account_names: List[str], category: str):
        """Выполняет удаление аккаунтов с автоматическим обновлением"""
        try:
            from src.accounts.manager import _account_manager

            logger.info(f"🗑️ Начинаем удаление {len(account_names)} аккаунтов")

            # Выполняем удаление
            results = _account_manager.delete_accounts(account_names, category)

            # Показываем результат через уведомления
            self._show_deletion_results(results)

            # Простое обновление только таблицы
            self._simple_refresh_after_deletion(category)

        except Exception as e:
            logger.error(f"❌ Критическая ошибка при удалении: {e}")
            show_error(
                "Критическая ошибка",
                f"❌ Критическая ошибка при удалении: {e}"
            )

    def handle_move_action(self):
        """Обрабатывает перемещение выбранных аккаунтов"""
        try:
            selected_accounts = self.table.get_selected_account_names()
            category = self.get_table_category()

            if not selected_accounts:
                show_info(
                    "Перемещение аккаунтов",
                    "Выберите аккаунты для перемещения"
                )
                return

            if not category:
                show_error(
                    "Ошибка",
                    "Не удалось определить категорию аккаунтов"
                )
                return

            # Получаем менеджер аккаунтов
            from src.accounts.manager import _account_manager

            if not _account_manager:
                show_error(
                    "Ошибка",
                    "Менеджер аккаунтов не инициализирован"
                )
                return

            # Получаем информацию об аккаунтах для перемещения
            accounts_info = []
            for account_name in selected_accounts:
                if category == "traffic":
                    account_data = _account_manager.traffic_accounts.get(account_name)
                elif category == "sales":
                    account_data = _account_manager.sales_accounts.get(account_name)
                else:
                    continue

                if account_data:
                    info = account_data.info
                    accounts_info.append({
                        'name': account_name,
                        'full_name': info.get('full_name', '?'),
                        'phone': info.get('phone', '?'),
                        'status': account_data.status,
                        'category': category
                    })

            # Получаем список доступных назначений
            # Определяем текущий статус (берем от первого аккаунта)
            current_status = accounts_info[0]['status'] if accounts_info else "unknown"
            destinations = _account_manager.get_move_destinations(category, current_status)

            if not destinations:
                show_warning(
                    "Нет доступных назначений",
                    "Не найдено папок для перемещения аккаунтов"
                )
                return

            # Показываем диалог перемещения
            selected_destination = self._show_move_dialog(accounts_info, destinations, category)

            if selected_destination:
                self._perform_move(selected_accounts, category, selected_destination)

        except Exception as e:
            logger.error(f"❌ Ошибка обработки перемещения: {e}")
            show_error(
                "Ошибка перемещения",
                f"Ошибка при перемещении: {e}"
            )

    def _show_move_dialog(self, accounts_info: List[Dict], destinations: List[Dict],
                         current_category: str) -> Optional[Dict]:
        """Показывает диалог выбора назначения для перемещения"""
        try:
            # Импортируем диалог перемещения
            from gui.dialogs.move_accounts_dialog import show_move_accounts_dialog

            # Находим родительское окно
            parent_window = self.table
            while parent_window.parent():
                parent_window = parent_window.parent()

            # Показываем диалог
            return show_move_accounts_dialog(
                parent=parent_window,
                accounts_info=accounts_info,
                destinations=destinations,
                current_category=current_category
            )
        except Exception as e:
            logger.error(f"❌ Ошибка показа диалога перемещения: {e}")
            return None

    def _perform_move(self, account_names: List[str], source_category: str,
                     destination: Dict):
        """Выполняет перемещение аккаунтов"""
        try:
            from src.accounts.manager import _account_manager

            target_category = destination['category']
            target_status = destination['status']

            logger.info(f"📦 Начинаем перемещение {len(account_names)} аккаунтов")
            logger.info(f"   Из: {source_category}")
            logger.info(f"   В: {target_category}/{target_status}")

            # Выполняем перемещение
            results = _account_manager.move_accounts(
                account_names, source_category, target_category, target_status
            )

            # Показываем результат
            self._show_move_results(results, destination)

            # Обновляем таблицу
            self._simple_refresh_after_move(source_category)

        except Exception as e:
            logger.error(f"❌ Критическая ошибка при перемещении: {e}")
            show_error(
                "Критическая ошибка",
                f"❌ Критическая ошибка при перемещении: {e}"
            )

    def _show_move_results(self, results: Dict[str, bool], destination: Dict):
        """Показывает результаты перемещения"""
        success_count = sum(1 for success in results.values() if success)
        failed_count = len(results) - success_count

        destination_name = destination['display_name']

        if failed_count == 0:
            # Успешное перемещение
            show_success(
                "Перемещение завершено",
                f"Успешно перемещено {success_count} аккаунт(ов)\n"
                f"Назначение: {destination_name}"
            )
        else:
            # Частичная ошибка
            failed_accounts = [name for name, success in results.items() if not success]
            show_error(
                "Ошибки при перемещении",
                f"Перемещено: {success_count}, ошибок: {failed_count}\n" +
                f"Назначение: {destination_name}\n" +
                f"Не удалось переместить: {', '.join(failed_accounts[:3])}" +
                (f" и еще {len(failed_accounts) - 3}" if len(failed_accounts) > 3 else "")
            )

    def handle_refresh_action(self):
        """Обрабатывает ручное обновление данных"""
        try:
            from src.accounts.manager import _account_manager
            import asyncio

            if not _account_manager:
                show_error(
                    "Ошибка",
                    "Менеджер аккаунтов не инициализирован"
                )
                return

            # Показываем что начали обновление
            self._set_refresh_state(True)

            # Уведомление о начале обновления
            show_info(
                "Обновление начато",
                "Пересканируем папки с аккаунтами..."
            )

            # Запускаем ПОЛНОЕ обновление (пересканирование папок)
            category = self.get_table_category()
            if category:
                # Обновляем только текущую категорию
                task = asyncio.create_task(_account_manager.refresh_category(category))
            else:
                # Полное обновление
                task = asyncio.create_task(_account_manager.refresh_all_accounts())

            # Обновляем таблицу после завершения
            task.add_done_callback(lambda t: self._on_manual_refresh_complete(t))

        except Exception as e:
            logger.error(f"❌ Ошибка обработки обновления: {e}")
            self._set_refresh_state(False)
            show_error(
                "Ошибка обновления",
                f"Ошибка при обновлении: {e}"
            )


    def _simple_refresh_after_deletion(self, category: str):
        """Простое обновление таблицы после удаления"""
        try:
            logger.info("🔄 Простое обновление таблицы после удаления...")

            # Небольшая задержка для корректного обновления
            QTimer.singleShot(300, lambda: self._update_table_only(category))

        except Exception as e:
            logger.error(f"❌ Ошибка простого обновления: {e}")

    def _simple_refresh_after_move(self, category: str):
        """Простое обновление таблицы после перемещения"""
        try:
            logger.info("🔄 Простое обновление таблицы после перемещения...")

            # Небольшая задержка для корректного обновления
            QTimer.singleShot(300, lambda: self._update_table_only(category))

        except Exception as e:
            logger.error(f"❌ Ошибка простого обновления: {e}")

    def _update_table_only(self, category: str):
        """Обновляет только данные таблицы для текущей папки"""
        try:
            from src.accounts.manager import get_table_data

            # Получаем текущий статус
            current_status = self.get_current_status()
            logger.info(f"📊 Обновляем таблицу для категории: {category}, статус: {current_status}")

            # ИСПРАВЛЕНО: Получаем ВСЕ данные для пагинации (без лимита)
            new_data = get_table_data(category, current_status, limit=-1)

            # Обновляем таблицу
            if hasattr(self.table, 'update_table_data'):
                self.table.update_table_data(new_data)
                logger.info(f"✅ Таблица обновлена, всего данных: {len(new_data)}")
            else:
                # Fallback - пересоздаем данные
                self.table.config['demo_data'] = new_data
                if hasattr(self.table, '_load_initial_data'):
                    self.table._load_initial_data()
                elif hasattr(self.table, '_fill_table_data'):
                    self.table._fill_table_data()
                logger.info("✅ Таблица обновлена через fallback метод")

            # Обновляем статистику в родительском компоненте
            self._update_parent_stats_only(category)

            # Показываем информацию о пагинации
            if hasattr(self.table, 'get_pagination_info'):
                pag_info = self.table.get_pagination_info()
                logger.info(f"📄 Пагинация: страница {pag_info['current_page']}/{pag_info['total_pages']}, показано {pag_info['per_page']} из {pag_info['total_items']}")

        except Exception as e:
            logger.error(f"❌ Ошибка обновления таблицы: {e}")

    def _update_parent_stats_only(self, category: str):
        """Обновляет только статистику в родительском компоненте"""
        try:
            from src.accounts.manager import get_traffic_stats, get_sales_stats

            # Ищем родительский компонент
            parent = self.table.parent()
            while parent:
                if hasattr(parent, 'stats_widget'):
                    logger.info("📊 Обновляем статистику в родительском компоненте")

                    # Получаем новую статистику
                    if category == "traffic":
                        new_stats = get_traffic_stats()
                    elif category == "sales":
                        new_stats = get_sales_stats()
                    else:
                        break

                    # Обновляем каждый элемент статистики
                    for i, (title, value, color) in enumerate(new_stats):
                        if i < len(parent.stats_widget.stat_boxes):
                            parent.stats_widget.update_stat(i, value)
                            logger.debug(f"   📊 Обновлен элемент {i}: {title} = {value}")

                    break
                parent = parent.parent()

        except Exception as e:
            logger.error(f"❌ Ошибка обновления статистики: {e}")

    def _show_deletion_results(self, results: dict):
        """Показывает результаты удаления с красивыми уведомлениями"""
        success_count = sum(1 for success in results.values() if success)
        failed_count = len(results) - success_count

        if failed_count == 0:
            # Успешное удаление
            show_success(
                "Удаление завершено",
                f"Успешно удалено {success_count} аккаунт(ов)\nТаблица обновлена автоматически"
            )
        else:
            # Частичная ошибка
            failed_accounts = [name for name, success in results.items() if not success]
            show_error(
                "Ошибки при удалении",
                f"Удалено: {success_count}, ошибок: {failed_count}\n" +
                f"Не удалось удалить: {', '.join(failed_accounts[:3])}" +
                (f" и еще {len(failed_accounts) - 3}" if len(failed_accounts) > 3 else "")
            )

    def _set_refresh_state(self, refreshing: bool):
        """Устанавливает состояние кнопки обновления"""
        if hasattr(self.table, 'update_btn'):
            if refreshing:
                self.table.update_btn.setText("⏳ Обновление...")
                self.table.update_btn.setEnabled(False)
            else:
                self.table.update_btn.setText("🔄 Обновить")
                self.table.update_btn.setEnabled(True)

    def _on_manual_refresh_complete(self, task):
        """Вызывается после завершения РУЧНОГО обновления"""
        try:
            # Возвращаем кнопку в нормальное состояние
            self._set_refresh_state(False)

            # Получаем результат
            result = task.result()

            # Полностью обновляем родительский компонент
            category = self.get_table_category()
            if category:
                parent = self.table.parent()
                while parent:
                    if hasattr(parent, 'refresh_data'):
                        logger.info("🔄 Полное обновление родительского компонента")
                        parent.refresh_data()
                        break
                    parent = parent.parent()

            # Показываем результат с учетом пагинации
            if isinstance(result, dict) and 'traffic_diff' in result:
                # Полное обновление
                traffic_diff = result['traffic_diff']
                sales_diff = result['sales_diff']

                if traffic_diff != 0 or sales_diff != 0:
                    show_success(
                        "Обновление завершено",
                        f"Изменения в аккаунтах:\nТрафик: {traffic_diff:+d}, Продажи: {sales_diff:+d}"
                    )
                else:
                    show_info(
                        "Обновление завершено",
                        "Изменений не обнаружено"
                    )
            else:
                # Обновление категории
                if isinstance(result, int):
                    # Показываем дополнительную информацию о пагинации
                    pag_info = ""
                    if hasattr(self.table, 'get_pagination_info'):
                        pag_data = self.table.get_pagination_info()
                        if pag_data['total_pages'] > 1:
                            pag_info = f"\n📄 Страница {pag_data['current_page']}/{pag_data['total_pages']}"

                    show_success(
                        "Обновление завершено",
                        f"Найдено аккаунтов: {result}{pag_info}"
                    )

        except Exception as e:
            logger.error(f"❌ Ошибка завершения обновления: {e}")
            self._set_refresh_state(False)
            show_error(
                "Ошибка обновления",
                f"Ошибка при завершении обновления: {e}"
            )

    # ИСПРАВЛЕННЫЕ МЕТОДЫ - убираем обращения к self.table.config
    def get_table_category(self) -> str:
        """Определяет категорию таблицы"""
        # Проверяем атрибуты таблицы
        if hasattr(self.table, 'category'):
            return self.table.category
        
        # Если нет атрибута category, пытаемся получить из config
        if hasattr(self.table, 'config') and 'category' in self.table.config:
            return self.table.config['category']
        
        # Определяем по родительскому компоненту
        parent = self.table.parent()
        while parent:
            if hasattr(parent, 'category'):
                return parent.category
            parent = parent.parent()
        
        # Последний fallback - возвращаем traffic по умолчанию
        logger.warning("⚠️ Не удалось определить категорию таблицы, используем 'traffic' по умолчанию")
        return 'traffic'

    def get_current_status(self) -> str:
        """Получает текущий статус (папку) таблицы"""
        # Проверяем атрибуты таблицы
        if hasattr(self.table, 'current_status'):
            return self.table.current_status
        
        # Если нет атрибута current_status, пытаемся получить из config
        if hasattr(self.table, 'config') and 'current_status' in self.table.config:
            return self.table.config['current_status']
        
        # Определяем по родительскому компоненту
        parent = self.table.parent()
        while parent:
            if hasattr(parent, 'current_status'):
                return parent.current_status
            parent = parent.parent()
        
        # Последний fallback - возвращаем статус по умолчанию для категории
        category = self.get_table_category()
        if category == "traffic":
            return "active"
        elif category == "sales":
            return "registration"
        else:
            return "active"