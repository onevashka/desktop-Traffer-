# src/entities/moduls/inviter.py - ОБНОВЛЕННАЯ ВЕРСИЯ
"""
Модели данных для модуля инвайтера с поддержкой админ-инвайтинга
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional
from paths import Path
import queue


class UserStatus(Enum):
    """Статусы пользователей для инвайта"""
    CLEAN = "clean"  # Чистый, готов к инвайту
    INVITED = "invited"  # Успешно приглашен
    ERROR = "error"  # Ошибка при инвайте
    PRIVACY = "privacy"  # Настройки приватности
    ALREADY_IN = "already_in"  # Уже в чате
    SPAM_BLOCK = "spam_block"  # Спамблок
    NOT_FOUND = "not_found"  # Пользователь не найден
    FLOOD_WAIT = "flood_wait"  # Ожидание флуда
    USER_ALREADY_CHATS = "user_already_chats"


@dataclass
class InviteUser:
    """Модель пользователя для инвайта"""
    username: str  # Username без @
    status: UserStatus = UserStatus.CLEAN
    last_attempt: Optional[datetime] = None
    error_message: Optional[str] = None

    def to_file_format(self) -> str:
        """Преобразует в формат для сохранения в файл"""
        if self.status == UserStatus.CLEAN:
            return f"@{self.username}"

        status_map = {
            UserStatus.INVITED: "✅ Приглашен",
            UserStatus.ERROR: f"❌ Ошибка",
            UserStatus.PRIVACY: "🔒 Приватность",
            UserStatus.ALREADY_IN: "👥 Уже в чате",
            UserStatus.SPAM_BLOCK: "🚫 Спамблок",
            UserStatus.NOT_FOUND: "❓ Не найден",
            UserStatus.FLOOD_WAIT: "⏳ Флуд"
        }

        status_text = status_map.get(self.status, str(self.status.value))
        if self.error_message and self.status == UserStatus.ERROR:
            status_text = f"{status_text}: {self.error_message}"

        return f"@{self.username}: {status_text}"


@dataclass
class AccountStats:
    """Статистика аккаунта в процессе инвайтинга"""
    name: str
    invites: int = 0
    errors: int = 0
    spam_blocks: int = 0
    consecutive_spam: int = 0
    status: str = "ready"


@dataclass
class ChatStats:
    """Статистика чата в процессе инвайтинга"""
    name: str
    processed: int = 0
    success: int = 0
    errors: int = 0
    consecutive_errors: int = 0


@dataclass
class InviterConfig:
    """
    Конфигурация инвайтера с поддержкой админ-инвайтинга
    """
    """Конфигурация админ-инвайтера"""
    # Основные параметры
    invite_type: str = "admin"
    threads_per_chat: int = 1

    # Лимиты успешных инвайтов
    success_per_chat: int = 2
    success_per_account: int = 1

    # Задержки
    delay_after_start: int = 5
    delay_between: int = 5

    # Лимиты спама и ошибок
    acc_spam_limit: int = 33
    acc_writeoff_limit: int = 24
    acc_block_invite_limit: int = 55

    # Лимиты по чатам
    chat_spam_accounts: int = 35
    chat_writeoff_accounts: int = 24
    chat_unknown_error_accounts: int = 15
    chat_freeze_accounts: int = 41

    # Общие лимиты
    chat_limit: int = 50
    account_limit: int = 100
    invite_delay: int = 30
    spam_errors: int = 3
    writeoff_limit: int = 2

    # Админ-специфичные настройки
    delay_between_workers: int = 10
    sequential_workers: bool = True
    admin_rights_timeout: int = 30
    # ========== НОВЫЕ ПОЛЯ ДЛЯ АДМИН-ИНВАЙТИНГА ==========
    # Настройки бота
    bot_token: str = ""  # Токен бота для управления правами

    # Главный админ
    main_admin_account: str = ""  # Имя аккаунта главного админа

    @classmethod
    def from_dict(cls, data: dict) -> 'InviterConfig':
        """Создает конфиг из словаря с фильтрацией полей"""
        # Фильтруем только известные поля
        known_fields = {field.name for field in cls.__dataclass_fields__.values()}
        filtered_data = {k: v for k, v in data.items() if k in known_fields}
        return cls(**filtered_data)

    def to_dict(self) -> dict:
        """Конвертирует в словарь"""
        return {
            'invite_type': self.invite_type,
            'threads_per_chat': self.threads_per_chat,
            'success_per_chat': self.success_per_chat,
            'success_per_account': self.success_per_account,
            'delay_after_start': self.delay_after_start,
            'delay_between': self.delay_between,
            'acc_spam_limit': self.acc_spam_limit,
            'acc_error_limit': self.acc_error_limit,
            'chat_error_limit': self.chat_error_limit,
            'bot_token': self.bot_token,
            'main_admin_account': self.main_admin_account,
            'delay_between_workers': self.delay_between_workers,
            'sequential_workers': self.sequential_workers,
            'admin_rights_timeout': self.admin_rights_timeout
        }

    def is_admin_inviter(self) -> bool:
        """Проверяет, является ли это админ-инвайтером"""
        return self.invite_type == "admin"

    def validate_admin_config(self) -> tuple[bool, list[str]]:
        """
        Валидирует настройки админ-инвайтера

        Returns:
            tuple[bool, list[str]]: (валидность, список_ошибок)
        """
        if not self.is_admin_inviter():
            return True, []

        errors = []

        # Проверяем токен бота
        if not self.bot_token.strip():
            errors.append("Не указан токен бота")
        elif ':' not in self.bot_token:
            errors.append("Неверный формат токена бота")

        # Проверяем главного админа
        if not self.main_admin_account.strip():
            errors.append("Не указан главный админ аккаунт")

        # Проверяем лимиты
        if self.success_per_chat < 0:
            errors.append("Лимит инвайтов на чат не может быть отрицательным")

        if self.success_per_account < 0:
            errors.append("Лимит инвайтов на аккаунт не может быть отрицательным")

        if self.threads_per_chat < 1:
            errors.append("Количество воркеров должно быть минимум 1")

        # Проверяем задержки
        if self.delay_between < 0:
            errors.append("Задержка между инвайтами не может быть отрицательной")

        if self.admin_rights_timeout < 10:
            errors.append("Таймаут прав должен быть минимум 10 секунд")

        return len(errors) == 0, errors


@dataclass
class AdminCommand:
    """Команда для главного админа"""
    action: str  # "GRANT_RIGHTS" или "REVOKE_RIGHTS"
    worker_name: str
    worker_user_id: int
    worker_access_hash: int
    chat_link: str
    response_queue: queue.Queue  # Для ответа воркеру
    username: str


@dataclass
class AccountErrorCounters:
    """Счетчики ошибок для аккаунта"""
    consecutive_spam_blocks: int = 0
    consecutive_writeoffs: int = 0
    consecutive_block_invites: int = 0

    def reset_all(self):
        """Сброс всех счетчиков"""
        self.consecutive_spam_blocks = 0
        self.consecutive_writeoffs = 0
        self.consecutive_block_invites = 0

    def reset_spam_blocks(self):
        """Сброс счетчика спам-блоков"""
        self.consecutive_spam_blocks = 0

    def reset_writeoffs(self):
        """Сброс счетчика списаний"""
        self.consecutive_writeoffs = 0

    def reset_block_invites(self):
        """Сброс счетчика блоков инвайтов"""
        self.consecutive_block_invites = 0


@dataclass
class ChatAdmin:
    """Информация о главном админе чата"""
    name: str
    account: Optional[object] = None
    session_path: Optional[Path] = None
    json_path: Optional[Path] = None
    is_ready: bool = False