# src/proxies/manager.py
"""
Простой менеджер прокси - читает напрямую из файла
"""

from typing import Optional, List, Dict
from pathlib import Path
from loguru import logger
import random

from paths import PROXY_FILE


class ProxyManager:
    """Менеджер прокси - читает из файла при каждом запросе"""

    def __init__(self):
        self.proxy_file = PROXY_FILE
        self.current_index = 0
        logger.info("🌐 ProxyManager инициализирован")

    def _read_proxies_from_file(self) -> List[str]:
        """Читает прокси из файла"""
        try:
            with open(self.proxy_file, 'r', encoding='utf-8') as f:
                lines = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            return lines
        except FileNotFoundError:
            logger.error(f"❌ Файл прокси не найден: {self.proxy_file}")
            return []
        except Exception as e:
            logger.error(f"❌ Ошибка чтения файла прокси: {e}")
            return []

    def _parse_proxy_line(self, line: str) -> Optional[Dict]:
        """
        Парсит строку прокси формата host:port:login:password

        Returns:
            Словарь для Telethon или None
        """
        try:
            parts = line.strip().split(':')
            if len(parts) != 4:
                logger.warning(f"⚠️ Неверный формат прокси: {line}")
                return None

            host, port, login, password = parts

            # Формируем словарь для Telethon
            return {
                'proxy_type': 'socks5',  # По умолчанию socks5
                'addr': host,
                'port': int(port),
                'username': login,
                'password': password,
                'rdns': True  # Remote DNS для socks5
            }

        except Exception as e:
            logger.error(f"❌ Ошибка парсинга прокси '{line}': {e}")
            return None

    def get_proxy(self, random_choice: bool = False) -> Optional[Dict]:
        """
        Получает прокси из файла

        Args:
            random_choice: Выбрать случайный или по порядку

        Returns:
            Словарь прокси для Telethon или None
        """
        proxies = self._read_proxies_from_file()

        if not proxies:
            logger.warning("⚠️ Нет прокси в файле")
            return None

        # Выбираем прокси
        if random_choice:
            proxy_line = random.choice(proxies)
        else:
            # По кругу
            proxy_line = proxies[self.current_index % len(proxies)]
            self.current_index += 1

        # Парсим и возвращаем
        proxy_dict = self._parse_proxy_line(proxy_line)


        return proxy_dict

    def get_proxy_for_account(self, account_name: str) -> Optional[Dict]:
        """
        Получает прокси для аккаунта (пока что просто следующий по порядку)

        Args:
            account_name: Имя аккаунта

        Returns:
            Словарь прокси для Telethon
        """
        return self.get_proxy(random_choice=False)

    def get_total_proxies(self) -> int:
        """Возвращает количество прокси в файле"""
        return len(self._read_proxies_from_file())


# Глобальный экземпляр
_proxy_manager: Optional[ProxyManager] = None


def get_proxy_manager() -> ProxyManager:
    """Получает глобальный экземпляр ProxyManager"""
    global _proxy_manager
    if _proxy_manager is None:
        _proxy_manager = ProxyManager()
    return _proxy_manager


# Функции для быстрого доступа
def get_proxy() -> Optional[Dict]:
    """Получает следующий прокси"""
    manager = get_proxy_manager()
    return manager.get_proxy()


def get_proxy_for_account(account_name: str) -> Optional[Dict]:
    """Получает прокси для аккаунта"""
    manager = get_proxy_manager()
    return manager.get_proxy_for_account(account_name)


def get_random_proxy() -> Optional[Dict]:
    """Получает случайный прокси"""
    manager = get_proxy_manager()
    return manager.get_proxy(random_choice=True)