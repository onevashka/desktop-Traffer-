# src/modules/impl/inviter/data_loader.py
"""
Загрузчик данных для инвайтера
Отвечает за загрузку и парсинг данных из файлов
"""

import re
import queue
from pathlib import Path
from typing import List, Tuple, Dict
from loguru import logger

from src.entities.modules.inviter import InviteUser, UserStatus, InviterConfig


class InviterDataLoader:
    """Загружает и подготавливает данные для инвайтера"""

    def __init__(self, profile_folder: Path):
        self.profile_folder = profile_folder

        # Паттерны для парсинга пользователей
        self.dirty_patterns = [
            (r'@(\w+):\s*(.+)', ':'),  # @user: Статус
            (r'@(\w+)\s+(.+)', ' '),  # @user Статус
            (r'@(\w+)\s*-\s*(.+)', '-')  # @user - Статус
        ]

    def load_config(self, config_dict: dict) -> InviterConfig:
        """Загружает конфигурацию"""
        logger.debug("⚙️ Загрузка конфигурации")
        return InviterConfig.from_dict(config_dict)

    def load_chats(self) -> Tuple[List[str], int]:
        """
        Загружает чаты из файла

        Returns:
            Tuple[список_чатов, количество]
        """
        chats_file = self.profile_folder / "База чатов.txt"

        if not chats_file.exists():
            logger.error(f"❌ Файл чатов не найден: {chats_file}")
            return [], 0

        try:
            content = chats_file.read_text(encoding='utf-8').strip()
            if not content:
                logger.error("❌ Файл чатов пустой")
                return [], 0

            chats = [line.strip() for line in content.split('\n') if line.strip()]
            logger.info(f"💬 Загружено чатов: {len(chats)}")

            return chats, len(chats)

        except Exception as e:
            logger.error(f"❌ Ошибка загрузки чатов: {e}")
            return [], 0

    def load_users(self) -> Tuple[queue.Queue, Dict[str, InviteUser], int, int]:
        """
        Загружает и фильтрует пользователей

        Returns:
            Tuple[очередь_чистых, словарь_обработанных, кол-во_чистых, кол-во_грязных]
        """
        users_file = self.profile_folder / "База юзеров.txt"

        if not users_file.exists():
            logger.error(f"❌ Файл пользователей не найден: {users_file}")
            return queue.Queue(), {}, 0, 0

        try:
            content = users_file.read_text(encoding='utf-8').strip()
            if not content:
                logger.error("❌ Файл пользователей пустой")
                return queue.Queue(), {}, 0, 0

            user_queue = queue.Queue()
            processed_users = {}
            clean_count = 0
            dirty_count = 0

            for line in content.split('\n'):
                line = line.strip()
                if not line:
                    continue

                # Проверяем на грязные паттерны
                user, is_dirty = self._parse_user_line(line)

                if user:
                    if is_dirty:
                        processed_users[user.username] = user
                        dirty_count += 1
                        logger.debug(f"🚫 Обработанный пользователь: {line}")
                    else:
                        user_queue.put(user)
                        clean_count += 1

            logger.info(f"👥 Загружено: {clean_count} чистых, {dirty_count} обработанных")

            return user_queue, processed_users, clean_count, dirty_count

        except Exception as e:
            logger.error(f"❌ Ошибка загрузки пользователей: {e}")
            return queue.Queue(), {}, 0, 0

    def _parse_user_line(self, line: str) -> Tuple[InviteUser, bool]:
        """
        Парсит строку с пользователем

        Returns:
            Tuple[InviteUser, is_dirty]
        """
        # Проверяем грязные паттерны
        for pattern, separator in self.dirty_patterns:
            match = re.match(pattern, line)
            if match:
                username = match.group(1)
                status_text = match.group(2)

                user = InviteUser(
                    username=username,
                    status=self._parse_status(status_text),
                    error_message=status_text if separator in line else None
                )
                return user, True

        # Чистый пользователь
        username = line.strip()
        if username.startswith('@'):
            username = username[1:]

        # Валидация username
        if username and self._is_valid_username(username):
            return InviteUser(username=username), False

        return None, False

    def _is_valid_username(self, username: str) -> bool:
        """Проверяет валидность username"""
        # Username должен быть 5-32 символа, начинаться с буквы
        return bool(re.match(r'^[a-zA-Z][a-zA-Z0-9_]{4,31}$', username))

    def _parse_status(self, status_text: str) -> UserStatus:
        """Парсит статус из текста"""
        status_lower = status_text.lower()

        status_map = {
            'приглашен': UserStatus.INVITED,
            '✅': UserStatus.INVITED,
            'приватность': UserStatus.PRIVACY,
            '🔒': UserStatus.PRIVACY,
            'уже в чате': UserStatus.ALREADY_IN,
            '👥': UserStatus.ALREADY_IN,
            'спамблок': UserStatus.SPAM_BLOCK,
            '🚫': UserStatus.SPAM_BLOCK,
            'не найден': UserStatus.NOT_FOUND,
            '❓': UserStatus.NOT_FOUND,
            'флуд': UserStatus.FLOOD_WAIT,
            '⏳': UserStatus.FLOOD_WAIT,
        }

        for key, status in status_map.items():
            if key in status_lower:
                return status

        return UserStatus.ERROR

    def save_users_progress(self, processed_users: Dict[str, InviteUser],
                            user_queue: queue.Queue):
        """Сохраняет прогресс обработки пользователей"""
        try:
            users_file = self.profile_folder / "База юзеров.txt"

            # Собираем всех пользователей
            all_lines = []

            # Сначала обработанные
            for user in processed_users.values():
                all_lines.append(user.to_file_format())

            # Затем необработанные из очереди
            temp_users = []
            while not user_queue.empty():
                try:
                    user = user_queue.get_nowait()
                    temp_users.append(user)
                    all_lines.append(user.to_file_format())
                except queue.Empty:
                    break

            # Возвращаем в очередь
            for user in temp_users:
                user_queue.put(user)

            # Сохраняем
            content = '\n'.join(all_lines)
            users_file.write_text(content, encoding='utf-8')

            logger.info(f"💾 Сохранено: {len(processed_users)} обработано, {len(temp_users)} в очереди")

        except Exception as e:
            logger.error(f"❌ Ошибка сохранения прогресса: {e}")