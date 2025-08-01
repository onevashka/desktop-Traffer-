# src/entities/modules/inviter.py
"""
Модели данных для модуля инвайтера
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


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
    """Конфигурация инвайтера"""
    # Основные параметры
    invite_type: str = "classic"
    threads_per_chat: int = 2

    # Лимиты
    success_per_chat: int = 0  # 0 = без ограничений
    success_per_account: int = 0

    # Задержки
    delay_after_start: int = 0
    delay_between: int = 30

    # Безопасность аккаунтов
    acc_spam_limit: int = 3
    acc_error_limit: int = 10

    # Безопасность чатов
    chat_error_limit: int = 3

    @classmethod
    def from_dict(cls, data: dict) -> 'InviterConfig':
        """Создает конфиг из словаря"""
        return cls(**{k: v for k, v in data.items() if hasattr(cls, k)})