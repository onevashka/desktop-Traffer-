from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

# Используем TYPE_CHECKING для типизации без реального импорта
if TYPE_CHECKING:
    from src.accounts.impl.account import Account


@dataclass
class AccountData:
    """Полная информация об аккаунте"""
    name: str  # имя аккаунта (без расширения)
    category: str  # "traffic" или "sales"
    status: str  # папка где лежит: "active", "dead", "frozen", etc.
    account: "Account"  # объект аккаунта с данными
    info: dict  # кешированная информация из account.get_info()