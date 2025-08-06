# src/modules/impl/inviter/progress_manager.py
"""
Модуль для управления прогрессом пользователей и сохранением данных
Вынесен из admin_inviter.py для лучшей организации кода
"""
import traceback
import threading
import queue
import json
from typing import Dict
from datetime import datetime
from loguru import logger
from pathlib import Path
from src.entities.moduls.inviter import *


class ProgressManager:
    """Менеджер для управления прогрессом пользователей"""

    def __init__(self, parent_process):
        self.parent = parent_process
        self.file_write_lock = threading.Lock()

    def save_users_progress_to_file(self):
        """
        Сохраняет прогресс пользователей в файл (thread-safe) БЕЗ БЭКАПОВ
        """
        try:
            with self.file_write_lock:  # Thread-safe запись
                logger.debug(f"💾 [{self.parent.profile_name}] Сохранение прогресса пользователей в файл...")

                # Собираем всех пользователей в правильном формате
                all_lines = []

                # 1. Сначала добавляем всех обработанных пользователей
                for username, user in self.parent.processed_users.items():
                    line = self._format_user_for_file(user)
                    if line:
                        all_lines.append(line)

                # 2. Затем добавляем оставшихся необработанных пользователей из очереди
                remaining_users = []
                try:
                    while not self.parent.user_queue.empty():
                        user = self.parent.user_queue.get_nowait()
                        remaining_users.append(user)
                        # Добавляем чистого пользователя
                        all_lines.append(f"@{user.username}")
                except queue.Empty:
                    pass

                # Возвращаем пользователей обратно в очередь
                for user in remaining_users:
                    self.parent.user_queue.put(user)

                # 3. Записываем прямо в основной файл БЕЗ БЭКАПА
                content = '\n'.join(all_lines)
                self.parent.users_file_path.write_text(content, encoding='utf-8', errors='replace')

                logger.info(f"   📊 Обработанных: {len(self.parent.processed_users)}")
                logger.info(f"   📊 Оставшихся: {len(remaining_users)}")

        except Exception as e:
            logger.error(f"❌ [{self.parent.profile_name}] КРИТИЧЕСКАЯ ошибка сохранения прогресса: {e}")
            logger.error(f"❌ [{self.parent.profile_name}] Стек ошибки:\n{traceback.format_exc()}")

    def _format_user_for_file(self, user: InviteUser) -> str:
        """
        Форматирует пользователя для записи в файл
        """
        try:
            username = user.username
            if not username.startswith('@'):
                username = f"@{username}"

            # Формируем статус и сообщение
            if user.status == UserStatus.INVITED:
                status_text = "✅ Приглашен"
            elif user.status == UserStatus.PRIVACY:
                status_text = "🔒 Настройки приватности"
            elif user.status == UserStatus.ALREADY_IN:
                status_text = "👥 Уже в чате"
            elif user.status == UserStatus.SPAM_BLOCK:
                status_text = "🚫 Спамблок"
            elif user.status == UserStatus.NOT_FOUND:
                status_text = "❓ Не найден"
            elif user.status == UserStatus.ERROR:
                status_text = f"❌ Ошибка: {user.error_message or 'Неизвестная'}"
            else:
                # Для чистых пользователей возвращаем просто username
                return username

            # Добавляем детали если есть
            if user.error_message and user.error_message != status_text:
                status_text += f" - {user.error_message}"

            return f"{username}: {status_text}"

        except Exception as e:
            logger.error(f"❌ Ошибка форматирования пользователя {user.username}: {e}")
            return f"@{user.username}: ❌ Ошибка форматирования"

    def load_user_statuses(self):
        """Загружает статусы пользователей из файла"""
        try:
            profile_folder = Path(self.parent.profile_data['folder_path'])
            status_file = profile_folder / "user_statuses.json"

            if status_file.exists():
                with open(status_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Загружаем пользователей
                for username, user_data in data.get('users', {}).items():
                    user = InviteUser(username=username)

                    # Правильная обработка enum статуса
                    status_value = user_data.get('status', 'NEW')
                    if isinstance(status_value, str):
                        # Пытаемся найти enum по значению
                        for status_enum in UserStatus:
                            if status_enum.value == status_value:
                                user.status = status_enum
                                break
                        else:
                            # Если не найден - устанавливаем NEW
                            user.status = UserStatus.NEW
                    else:
                        user.status = UserStatus.NEW

                    user.last_attempt = datetime.fromisoformat(user_data['last_attempt']) if user_data.get(
                        'last_attempt') else None
                    user.error_message = user_data.get('error_message')
                    self.parent.processed_users[username] = user

                logger.success(
                    f"[{self.parent.profile_name}] Загружено статусов пользователей: {len(self.parent.processed_users)}")
            else:
                logger.info(
                    f"[{self.parent.profile_name}] Файл статусов пользователей не найден, начинаем с чистого листа")

        except Exception as e:
            logger.error(f"[{self.parent.profile_name}] Ошибка загрузки статусов пользователей: {e}")

    def save_user_statuses(self):
        """Сохраняет статусы пользователей в файл"""
        try:
            profile_folder = Path(self.parent.profile_data['folder_path'])
            status_file = profile_folder / "user_statuses.json"

            data = {
                'users': {},
                'last_updated': datetime.now().isoformat()
            }

            # Сохраняем статусы пользователей
            for username, user in self.parent.processed_users.items():
                data['users'][username] = {
                    'status': user.status.value if hasattr(user.status, 'value') else str(user.status),
                    'last_attempt': user.last_attempt.isoformat() if user.last_attempt else None,
                    'error_message': user.error_message
                }

            with open(status_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            logger.success(
                f"[{self.parent.profile_name}] Сохранено статусов пользователей: {len(self.parent.processed_users)}")

        except Exception as e:
            logger.error(f"[{self.parent.profile_name}] Ошибка сохранения статусов пользователей: {e}")