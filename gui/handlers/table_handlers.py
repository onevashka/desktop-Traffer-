"""
Обработчики действий с таблицами аккаунтов - с автоматическим обновлением
"""

from typing import List
from PySide6.QtWidgets import QMessageBox
from PySide6.QtCore import QTimer
from loguru import logger

# Импортируем систему уведомлений
from gui.notifications import show_success, show_error, show_warning, show_info


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
            category = self.table.get_table_category()

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

            # Получаем информацию об аккаунтах
            accounts_info = _account_manager.get_account_info_for_deletion(selected_accounts, category)

            # Показываем диалог подтверждения
            if self._confirm_deletion(accounts_info):
                self._perform_deletion(selected_accounts, category)

        except Exception as e:
            logger.error(f"❌ Ошибка обработки удаления: {e}")
            show_error(
                "Критическая ошибка",
                f"Ошибка при удалении: {e}"
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

            # ИСПРАВЛЕНО: Простое обновление только таблицы
            self._simple_refresh_after_deletion(category)

        except Exception as e:
            logger.error(f"❌ Критическая ошибка при удалении: {e}")
            show_error(
                "Критическая ошибка",
                f"❌ Критическая ошибка при удалении: {e}"
            )

    def _auto_refresh_after_deletion(self, category: str):
        """Автоматически обновляет таблицу после удаления"""
        try:
            logger.info("🔄 Автоматическое обновление таблицы после удаления...")

            # Небольшая задержка для корректного обновления
            QTimer.singleShot(200, lambda: self._refresh_table_data(category))

        except Exception as e:
            logger.error(f"❌ Ошибка автоматического обновления: {e}")

    def _refresh_table_data(self, category: str):
        """Обновляет данные таблицы"""
        try:
            from src.accounts.manager import get_table_data

            logger.info(f"📊 Обновляем данные таблицы для категории: {category}")

            # Получаем новые данные
            new_data = get_table_data(category, limit=50)

            # Обновляем таблицу
            if hasattr(self.table, 'update_table_data'):
                self.table.update_table_data(new_data)
                logger.info(f"✅ Таблица обновлена, показано {len(new_data)} аккаунтов")
            else:
                # Fallback - пересоздаем данные
                self.table.config['demo_data'] = new_data
                self.table._fill_table_data()
                logger.info("✅ Таблица обновлена через fallback метод")

            # Обновляем статистику в родительском компоненте
            self._refresh_parent_statistics()

        except Exception as e:
            logger.error(f"❌ Ошибка обновления данных таблицы: {e}")

    def _refresh_parent_statistics(self):
        """Обновляет статистику в родительском компоненте"""
        try:
            # Ищем родительский компонент (TrafficAccountsTab или SalesAccountsTab)
            parent = self.table.parent()
            while parent:
                if hasattr(parent, 'refresh_data'):
                    logger.info("📊 Обновляем статистику в родительском компоненте")
                    parent.refresh_data()
                    break
                parent = parent.parent()
        except Exception as e:
            logger.error(f"❌ Ошибка обновления статистики: {e}")

    def handle_move_action(self):
        """Обрабатывает перемещение выбранных аккаунтов"""
        try:
            selected_accounts = self.table.get_selected_account_names()
            category = self.table.get_table_category()

            if not selected_accounts:
                show_info(
                    "Перемещение аккаунтов",
                    "Выберите аккаунты для перемещения"
                )
                return

            # Открываем диалог выбора назначения
            self._show_move_dialog(selected_accounts, category)

        except Exception as e:
            logger.error(f"❌ Ошибка обработки перемещения: {e}")
            show_error(
                "Ошибка перемещения",
                f"Ошибка при перемещении: {e}"
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
            category = self.table.get_table_category()
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
    def _confirm_deletion(self, accounts_info: List[dict]) -> bool:
        """Показывает диалог подтверждения удаления"""
        if not accounts_info:
            show_warning("Ошибка", "Аккаунты не найдены")
            return False

        # Формируем текст подтверждения
        confirm_text = f"Вы действительно хотите удалить {len(accounts_info)} аккаунт(ов)?\n\n"
        confirm_text += "Будут удалены следующие аккаунты:\n"

        for info in accounts_info[:5]:  # Показываем первые 5
            full_name = info.get('full_name', '?')
            status = info.get('status', '?')
            confirm_text += f"• {info['name']} ({full_name}) - {status}\n"

        if len(accounts_info) > 5:
            confirm_text += f"... и еще {len(accounts_info) - 5} аккаунт(ов)\n"

        confirm_text += f"\n⚠️ ВНИМАНИЕ: Файлы .session и .json будут удалены безвозвратно!\n"
        confirm_text += f"📊 Таблица будет автоматически обновлена после удаления."

        # Показываем стандартный диалог Qt (для важных операций)
        reply = QMessageBox.question(
            self.table,
            "Подтверждение удаления",
            confirm_text,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        return reply == QMessageBox.Yes

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

    def _show_move_dialog(self, account_names: List[str], source_category: str):
        """Показывает информацию о перемещении (пока заглушка)"""
        show_info(
            "Перемещение аккаунтов",
            f"Функция перемещения {len(account_names)} аккаунт(ов) из {source_category}\n" +
            "будет реализована в следующем обновлении"
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

    def _on_refresh_complete(self, task):
        """Вызывается после завершения ручного обновления"""
        try:
            # Возвращаем кнопку в нормальное состояние
            self._set_refresh_state(False)

            # Получаем результат
            result = task.result()

            # Обновляем таблицу
            category = self.table.get_table_category()
            if category:
                self._refresh_table_data(category)

            # Показываем результат
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
                    show_success(
                        "Обновление завершено",
                        f"Найдено аккаунтов: {result}"
                    )

        except Exception as e:
            logger.error(f"❌ Ошибка завершения обновления: {e}")
            self._set_refresh_state(False)
            show_error(
                "Ошибка обновления",
                f"Ошибка при завершении обновления: {e}"
            )

    def _simple_refresh_after_deletion(self, category: str):
        """Простое обновление таблицы после удаления"""
        try:
            logger.info("🔄 Простое обновление таблицы после удаления...")

            # Небольшая задержка для корректного обновления
            QTimer.singleShot(300, lambda: self._update_table_only(category))

        except Exception as e:
            logger.error(f"❌ Ошибка простого обновления: {e}")

    def _update_table_only(self, category: str):
        """Обновляет только данные таблицы"""
        try:
            from src.accounts.manager import get_table_data, get_traffic_stats, get_sales_stats

            logger.info(f"📊 Обновляем только таблицу для категории: {category}")

            # Получаем новые данные таблицы
            new_data = get_table_data(category, limit=50)

            # Обновляем таблицу
            if hasattr(self.table, 'update_table_data'):
                self.table.update_table_data(new_data)
                logger.info(f"✅ Таблица обновлена, показано {len(new_data)} аккаунтов")
            else:
                # Fallback - пересоздаем данные
                self.table.config['demo_data'] = new_data
                if hasattr(self.table, '_fill_table_data'):
                    self.table._fill_table_data()
                logger.info("✅ Таблица обновлена через fallback метод")

            # Обновляем статистику в родительском компоненте
            self._update_parent_stats_only(category)

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

    def _on_manual_refresh_complete(self, task):
        """Вызывается после завершения РУЧНОГО обновления"""
        try:
            # Возвращаем кнопку в нормальное состояние
            self._set_refresh_state(False)

            # Получаем результат
            result = task.result()

            # Полностью обновляем родительский компонент
            category = self.table.get_table_category()
            if category:
                parent = self.table.parent()
                while parent:
                    if hasattr(parent, 'refresh_data'):
                        logger.info("🔄 Полное обновление родительского компонента")
                        parent.refresh_data()
                        break
                    parent = parent.parent()

            # Показываем результат
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
                    show_success(
                        "Обновление завершено",
                        f"Найдено аккаунтов: {result}"
                    )

        except Exception as e:
            logger.error(f"❌ Ошибка завершения обновления: {e}")
            self._set_refresh_state(False)
            show_error(
                "Ошибка обновления",
                f"Ошибка при завершении обновления: {e}"
            )