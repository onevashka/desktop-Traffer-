# src/utils/folder_utils.py
"""
Утилиты для работы с папками - открытие в проводнике
"""

import os
import subprocess
import platform
from pathlib import Path
from loguru import logger


class FolderManager:
    """Менеджер для работы с папками"""

    @staticmethod
    def open_folder_in_explorer(folder_path: Path) -> bool:
        """
        Открывает папку в проводнике операционной системы

        Args:
            folder_path: Путь к папке

        Returns:
            True если успешно открыто, False если ошибка
        """
        try:
            # Убеждаемся что папка существует
            if not folder_path.exists():
                folder_path.mkdir(parents=True, exist_ok=True)
                logger.info(f"📁 Создана папка: {folder_path}")

            # Получаем абсолютный путь
            abs_path = folder_path.resolve()

            # Определяем операционную систему и открываем соответственно
            system = platform.system().lower()

            if system == "windows":
                # Windows - используем explorer
                subprocess.Popen(f'explorer "{abs_path}"', shell=True)
                logger.info(f"📂 Открыта папка в Windows Explorer: {abs_path}")

            elif system == "darwin":  # macOS
                # macOS - используем open
                subprocess.Popen(["open", str(abs_path)])
                logger.info(f"📂 Открыта папка в macOS Finder: {abs_path}")

            elif system == "linux":
                # Linux - пробуем различные файловые менеджеры
                file_managers = ["xdg-open", "nautilus", "dolphin", "thunar", "pcmanfm"]

                for fm in file_managers:
                    try:
                        subprocess.Popen([fm, str(abs_path)])
                        logger.info(f"📂 Открыта папка в Linux ({fm}): {abs_path}")
                        break
                    except FileNotFoundError:
                        continue
                else:
                    logger.warning(f"⚠️ Не найден файловый менеджер для Linux")
                    return False

            else:
                logger.warning(f"⚠️ Неподдерживаемая ОС: {system}")
                return False

            return True

        except Exception as e:
            logger.error(f"❌ Ошибка открытия папки {folder_path}: {e}")
            return False

    @staticmethod
    def get_add_accounts_folder(category: str, current_status: str = None) -> Path:
        """
        Возвращает папку для добавления аккаунтов в зависимости от категории

        Args:
            category: "traffic" или "sales"
            current_status: текущий статус (опционально)

        Returns:
            Path к папке для добавления аккаунтов
        """
        from paths import WORK_ACCOUNTS_TRAFFER_FOLDER, WORK_ACCOUNTS_SALE_FOLDER

        if category == "traffic":
            # Для трафика - папка "Для работы"
            folder = WORK_ACCOUNTS_TRAFFER_FOLDER
            logger.debug(f"📁 Папка для добавления трафика: {folder}")

        elif category == "sales":
            # Для продаж - папка "Регистрация"
            folder = WORK_ACCOUNTS_SALE_FOLDER
            logger.debug(f"📁 Папка для добавления продаж: {folder}")

        else:
            # Fallback - корневая папка
            folder = Path("Аккаунты")
            logger.warning(f"⚠️ Неизвестная категория {category}, используем: {folder}")

        return folder

    @staticmethod
    def open_add_accounts_folder(category: str, current_status: str = None) -> bool:
        """
        Открывает папку для добавления аккаунтов

        Args:
            category: "traffic" или "sales"
            current_status: текущий статус (опционально)

        Returns:
            True если успешно открыто
        """
        folder = FolderManager.get_add_accounts_folder(category, current_status)

        logger.info(f"📂 Открываем папку для добавления аккаунтов ({category}): {folder}")
        return FolderManager.open_folder_in_explorer(folder)

    @staticmethod
    def open_current_folder(category: str, status: str) -> bool:
        """
        Открывает папку текущего статуса

        Args:
            category: "traffic" или "sales"
            status: статус аккаунтов

        Returns:
            True если успешно открыто
        """
        try:
            from src.accounts.manager import _account_manager

            if not _account_manager:
                logger.error("❌ Менеджер аккаунтов не инициализирован")
                return False

            # Получаем путь к папке статуса
            if category == "traffic":
                folder = _account_manager.traffic_folders.get(status)
            elif category == "sales":
                folder = _account_manager.sales_folders.get(status)
            else:
                logger.error(f"❌ Неизвестная категория: {category}")
                return False

            if not folder:
                logger.error(f"❌ Не найдена папка для {category}/{status}")
                return False

            logger.info(f"📂 Открываем папку текущего статуса ({category}/{status}): {folder}")
            return FolderManager.open_folder_in_explorer(folder)

        except Exception as e:
            logger.error(f"❌ Ошибка открытия папки {category}/{status}: {e}")
            return False

    @staticmethod
    def open_archives_folder() -> bool:
        """Открывает папку с архивами"""
        archives_folder = Path("Архивы")
        logger.info(f"📂 Открываем папку архивов: {archives_folder}")
        return FolderManager.open_folder_in_explorer(archives_folder)

    @staticmethod
    def open_root_accounts_folder() -> bool:
        """Открывает корневую папку аккаунтов"""
        root_folder = Path("Аккаунты")
        logger.info(f"📂 Открываем корневую папку аккаунтов: {root_folder}")
        return FolderManager.open_folder_in_explorer(root_folder)


# Удобные функции для быстрого доступа

def open_add_accounts_folder(category: str, current_status: str = None) -> bool:
    """Быстрая функция для открытия папки добавления аккаунтов"""
    return FolderManager.open_add_accounts_folder(category, current_status)


def open_current_folder(category: str, status: str) -> bool:
    """Быстрая функция для открытия текущей папки"""
    return FolderManager.open_current_folder(category, status)


def open_archives_folder() -> bool:
    """Быстрая функция для открытия папки архивов"""
    return FolderManager.open_archives_folder()


def open_root_accounts_folder() -> bool:
    """Быстрая функция для открытия корневой папки"""
    return FolderManager.open_root_accounts_folder()