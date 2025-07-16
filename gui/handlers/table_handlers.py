"""
Обработчики действий с таблицами аккаунтов
"""

from typing import List
from PySide6.QtWidgets import QMessageBox
from loguru import logger


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
                QMessageBox.information(
                    self.table,
                    "Удаление аккаунтов",
                    "Выберите аккаунты для удаления"
                )
                return

            if not category:
                QMessageBox.warning(
                    self.table,
                    "Ошибка",
                    "Не удалось определить категорию аккаунтов"
                )
                return

            # Получаем менеджер аккаунтов
            from src.accounts.manager import _account_manager

            if not _account_manager:
                QMessageBox.warning(
                    self.table,
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
            QMessageBox.critical(
                self.table,
                "Ошибка",
                f"Ошибка при удалении: {e}"
            )

    def handle_move_action(self):
        """Обрабатывает перемещение выбранных аккаунтов"""
        try:
            selected_accounts = self.table.get_selected_account_names()
            category = self.table.get_table_category()

            if not selected_accounts:
                QMessageBox.information(
                    self.table,
                    "Перемещение аккаунтов",
                    "Выберите аккаунты для перемещения"
                )
                return

            # Открываем диалог выбора назначения
            self._show_move_dialog(selected_accounts, category)

        except Exception as e:
            logger.error(f"❌ Ошибка обработки перемещения: {e}")
            QMessageBox.critical(
                self.table,
                "Ошибка",
                f"Ошибка при перемещении: {e}"
            )

    def handle_refresh_action(self):
        """Обрабатывает обновление данных"""
        try:
            from src.accounts.manager import _account_manager
            import asyncio

            if not _account_manager:
                QMessageBox.warning(
                    self.table,
                    "Ошибка",
                    "Менеджер аккаунтов не инициализирован"
                )
                return

            # Показываем что начали обновление
            self._set_refresh_state(True)

            # Запускаем обновление
            category = self.table.get_table_category()
            if category:
                # Обновляем только текущую категорию
                task = asyncio.create_task(_account_manager.refresh_category(category))
            else:
                # Полное обновление
                task = asyncio.create_task(_account_manager.refresh_all_accounts())

            # Обновляем таблицу после завершения
            task.add_done_callback(lambda t: self._on_refresh_complete(t))

        except Exception as e:
            logger.error(f"❌ Ошибка обработки обновления: {e}")
            self._set_refresh_state(False)
            QMessageBox.critical(
                self.table,
                "Ошибка",
                f"Ошибка при обновлении: {e}"
            )

    def _confirm_deletion(self, accounts_info: List[dict]) -> bool:
        """Показывает диалог подтверждения удаления"""
        if not accounts_info:
            QMessageBox.warning(self.table, "Ошибка", "Аккаунты не найдены")
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

        confirm_text += f"\n⚠️ ВНИМАНИЕ: Файлы .session и .json будут удалены безвозвратно!"

        # Показываем диалог
        reply = QMessageBox.question(
            self.table,
            "Подтверждение удаления",
            confirm_text,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        return reply == QMessageBox.Yes

    def _perform_deletion(self, account_names: List[str], category: str):
        """Выполняет удаление аккаунтов"""
        try:
            from src.accounts.manager import _account_manager

            # Выполняем удаление
            results = _account_manager.delete_accounts(account_names, category)

            # Показываем результат
            self._show_deletion_results(results)

            # Обновляем таблицу
            self.table.refresh_data()

        except Exception as e:
            logger.error(f"❌ Критическая ошибка при удалении: {e}")
            QMessageBox.critical(
                self.table,
                "Ошибка удаления",
                f"❌ Критическая ошибка при удалении: {e}"
            )

    def _show_refresh_result(self, result):
        """Показывает результат обновления"""
        from gui.notifications import show_success, show_info

        if isinstance(result, dict) and 'traffic_diff' in result:
            # Полное обновление
            show_success(
                "Обновление завершено",
                f"Трафик: {result['traffic_diff']:+d}, Продажи: {result['sales_diff']:+d}"
            )
        else:
            # Обновление категории
            show_info(
                "Обновление завершено",
                f"Загружено аккаунтов: {result}"
            )

    def _show_deletion_results(self, results: dict):
        """Показывает результаты удаления с красивыми уведомлениями"""
        from gui.notifications import show_success, show_error

        success_count = sum(1 for success in results.values() if success)
        failed_count = len(results) - success_count

        if failed_count == 0:
            # Успешное удаление
            show_success(
                "Удаление завершено",
                f"Успешно удалено {success_count} аккаунт(ов)"
            )
        else:
            # Частичная ошибка
            failed_accounts = [name for name, success in results.items() if not success]
            show_error(
                "Ошибки при удалении",
                f"Удалено: {success_count}, ошибок: {failed_count}"
            )

    def _show_move_dialog(self, account_names: List[str], source_category: str):
        """Показывает диалог выбора папки для перемещения"""
        # TODO: Реализовать диалог перемещения
        QMessageBox.information(
            self.table,
            "Перемещение",
            f"Функция перемещения {len(account_names)} аккаунт(ов) из {source_category}\n" +
            "Будет реализована в следующем этапе"
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
        """Вызывается после завершения обновления"""
        try:
            # Возвращаем кнопку в нормальное состояние
            self._set_refresh_state(False)

            # Обновляем таблицу
            self.table.refresh_data()

            # Показываем результат если нужно
            result = task.result()
            if isinstance(result, dict) and 'traffic_diff' in result:
                # Полное обновление
                QMessageBox.information(
                    self.table,
                    "Обновление завершено",
                    f"✅ Обновление завершено\n" +
                    f"Трафик: {result['traffic_diff']:+d}\n" +
                    f"Продажи: {result['sales_diff']:+d}"
                )
            else:
                # Обновление категории
                QMessageBox.information(
                    self.table,
                    "Обновление завершено",
                    f"✅ Загружено аккаунтов: {result}"
                )

        except Exception as e:
            logger.error(f"❌ Ошибка завершения обновления: {e}")
            self._set_refresh_state(False)