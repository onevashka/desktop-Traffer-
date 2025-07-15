# src/accounts/manager.py
from pathlib import Path
from typing import Dict, List, Optional

from src.accounts.impl.account import Account
from paths import *

class AccountManager:
    """
    Менеджер аккаунтов: сканирует директорию, хранит Accounts и задачи для них.
    """
    def __init__(self, accounts_dir: Path):
        self.accounts_dir = accounts_dir
        self._accounts: Dict[str, Account] = {}
        self._tasks: Dict[str, List[str]] = {}
        self.refresh()

    def refresh(self) -> None:
        """
        Обновляет внутренний словарь аккаунтов:
        - Добавляет новые из папки
        - Удаляет те, которые исчезли
        """
        current = {p.stem for p in self.accounts_dir.glob("*.json")}
        # Удаляем исчезнувшие
        for name in list(self._accounts):
            if name not in current:
                del self._accounts[name]
                del self._tasks[name]
        # Добавляем новые
        for name in current:
            if name not in self._accounts:
                json_path = self.accounts_dir / f"{name}.json"
                sess_path = self.accounts_dir / f"{name}.session"
                if sess_path.exists():
                    acc = Account(sess_path, json_path)
                    self._accounts[name] = acc
                    self._tasks[name] = []

    def list_accounts(self) -> List[str]:
        """Список имён всех аккаунтов."""
        return list(self._accounts.keys())

    def get_account(self, name: str) -> Optional[Account]:
        """Возвращает объект Account по имени или None."""
        return self._accounts.get(name)

    def remove_account(self, name: str) -> bool:
        """
        Удаляет аккаунт:
        - стирает файлы .json и .session,
        - убирает из менеджера и задач.
        Возвращает True, если удаление прошло (была найдена запись).
        """
        acc = self._accounts.get(name)
        if not acc:
            return False
        # удаляем файлы
        try:
            acc.json_path.unlink()
            acc.session_path.unlink()
        except Exception:
            pass
        # удаляем из словарей
        del self._accounts[name]
        del self._tasks[name]
        return True

    def assign_task(self, name: str, task: str) -> None:
        """Назначить текстовую задачу аккаунту."""
        if name in self._tasks:
            self._tasks[name].append(task)

    def get_tasks(self, name: str) -> List[str]:
        """Получить все задачи, назначенные аккаунту."""
        return list(self._tasks.get(name, []))

    def clear_tasks(self, name: str) -> None:
        """Очистить все задачи для аккаунта."""
        if name in self._tasks:
            self._tasks[name].clear()
