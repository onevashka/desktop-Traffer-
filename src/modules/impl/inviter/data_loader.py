# src/modules/impl/inviter/data_loader.py - ПРОСТОЕ ОБНОВЛЕНИЕ
"""
Загрузчик данных для инвайтера с поддержкой админ-инвайтинга
"""

import re
import queue
import datetime
from pathlib import Path
from typing import List, Tuple, Dict
from loguru import logger

from src.entities.moduls.inviter import InviteUser, UserStatus, InviterConfig


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
        """Загружает конфигурацию с поддержкой админ-инвайтинга"""
        logger.debug("⚙️ Загрузка конфигурации")

        # Создаем конфиг из словаря
        config = InviterConfig.from_dict(config_dict)

        # Если это админ-инвайтер, загружаем дополнительные данные
        if config.is_admin_inviter():
            # Загружаем токен бота из файла если не указан в конфиге
            if not config.bot_token:
                config.bot_token = self._load_bot_token()

            logger.debug(
                f"🤖 Админ-инвайтер: токен={'есть' if config.bot_token else 'нет'}, админ={config.main_admin_account}")

        return config

    def _load_bot_token(self) -> str:
        """Загружает токен бота из файла (ТОЛЬКО ИЗ ФАЙЛОВ, НЕ ИЗ КОНФИГА!)"""
        try:
            # 1. Сначала пробуем bot_tokens.txt (множественный)
            tokens_file = self.profile_folder / "bot_tokens.txt"
            if tokens_file.exists():
                content = tokens_file.read_text(encoding='utf-8').strip()
                tokens = [line.strip() for line in content.split('\n') if line.strip()]
                if tokens:
                    logger.debug("🤖 Токен бота загружен из bot_tokens.txt")
                    return tokens[0]  # Возвращаем первый токен

            # 2. Пробуем bot_token.txt (legacy формат)
            token_file = self.profile_folder / "bot_token.txt"
            if token_file.exists():
                token = token_file.read_text(encoding='utf-8').strip()
                if token:
                    logger.debug("🤖 Токен бота загружен из bot_token.txt")
                    return token

            logger.debug("⚠️ Токен бота не найден ни в одном файле")
            return ""

        except Exception as e:
            logger.error(f"❌ Ошибка загрузки токена бота: {e}")
            return ""

    def save_bot_token(self, token: str) -> bool:
        """Сохраняет токен бота в файл"""
        try:
            token_file = self.profile_folder / "bot_token.txt"
            token_file.write_text(token.strip(), encoding='utf-8')
            logger.info("💾 Токен бота сохранен")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения токена: {e}")
            return False

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

            chats = [line.strip() for line in content.split('\n') if line.strip() and not line.startswith('#')]
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
                if not line or line.startswith('#'):
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
        Парсит строку пользователя

        Returns:
            Tuple[пользователь, грязный_ли]
        """
        try:
            # Проверяем на грязные паттерны (уже обработанные)
            for pattern, separator in self.dirty_patterns:
                match = re.match(pattern, line, re.IGNORECASE)
                if match:
                    username = match.group(1)
                    status_text = match.group(2).strip()

                    # Определяем статус
                    status = UserStatus.ERROR  # По умолчанию
                    if "приглашен" in status_text.lower() or "✅" in status_text:
                        status = UserStatus.INVITED
                    elif "приватность" in status_text.lower() or "🔒" in status_text:
                        status = UserStatus.PRIVACY
                    elif "уже в чате" in status_text.lower() or "👥" in status_text:
                        status = UserStatus.ALREADY_IN
                    elif "спамблок" in status_text.lower() or "🚫" in status_text:
                        status = UserStatus.SPAM_BLOCK
                    elif "не найден" in status_text.lower() or "❓" in status_text:
                        status = UserStatus.NOT_FOUND

                    user = InviteUser(username=username, status=status, error_message=status_text)
                    return user, True  # Грязный

            # Чистая строка - извлекаем username
            if line.startswith('@'):
                username = line[1:].strip()
            else:
                username = line.strip()

            # Валидация username
            if re.match(r'^[a-zA-Z0-9_]{5,32}$', username):
                user = InviteUser(username=username, status=UserStatus.CLEAN)
                return user, False  # Чистый
            else:
                return None, False

        except Exception as e:
            logger.error(f"❌ Ошибка парсинга строки: {line}, ошибка: {e}")
            return None, False

    def save_users_progress(self, processed_users: Dict[str, InviteUser], remaining_queue: queue.Queue):
        """Сохраняет прогресс обработки пользователей"""
        try:
            users_file = self.profile_folder / "База юзеров.txt"
            backup_file = self.profile_folder / f"База юзеров_backup_{int(datetime.datetime.now().timestamp())}.txt"

            # Делаем бэкап
            if users_file.exists():
                import shutil
                shutil.copy2(users_file, backup_file)

            # Собираем всех пользователей
            all_lines = []

            # Добавляем обработанных
            for user in processed_users.values():
                all_lines.append(user.to_file_format())

            # Добавляем оставшихся чистых
            while not remaining_queue.empty():
                try:
                    user = remaining_queue.get_nowait()
                    all_lines.append(user.to_file_format())
                except queue.Empty:
                    break

            # Сохраняем
            users_file.write_text('\n'.join(all_lines), encoding='utf-8')
            logger.info(f"💾 Прогресс сохранен: {len(all_lines)} пользователей")

        except Exception as e:
            logger.error(f"❌ Ошибка сохранения прогресса: {e}")

    def validate_admin_profile(self, config: InviterConfig) -> Tuple[bool, List[str]]:
        """Простая валидация админ-профиля"""
        if not config.is_admin_inviter():
            return True, []

        errors = []

        # Проверяем конфигурацию
        config_valid, config_errors = config.validate_admin_config()
        errors.extend(config_errors)

        # Проверяем файлы
        chats, chats_count = self.load_chats()
        if chats_count == 0:
            errors.append("База чатов пуста")

        users_queue, processed_users, clean_count, dirty_count = self.load_users()
        if clean_count == 0:
            errors.append("Нет пользователей для инвайта")

        return len(errors) == 0, errors