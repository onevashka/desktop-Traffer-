# src/accounts/operations/archive_operations.py
"""
Операции архивации аккаунтов
"""

import shutil
import subprocess
from pathlib import Path
from typing import List, Dict
from loguru import logger
from datetime import datetime


class AccountArchiver:
    """Класс для операций архивации аккаунтов"""

    def __init__(self, account_manager):
        self.manager = account_manager
        self.archive_base_path = Path("Архивы")
        self.archive_base_path.mkdir(exist_ok=True)

    def archive_accounts(self, account_names: List[str], category: str,
                         archive_name: str, archive_format: str) -> Dict[str, any]:
        """
        Архивирует аккаунты с созданием папки и архива

        Args:
            account_names: Список имен аккаунтов
            category: Категория аккаунтов
            archive_name: Имя архива
            archive_format: Формат архива ('zip' или 'rar')

        Returns:
            Словарь с результатами операции
        """
        try:
            logger.info(f"📦 Начинаем архивацию {len(account_names)} аккаунтов")
            logger.info(f"   Категория: {category}")
            logger.info(f"   Имя архива: {archive_name}")
            logger.info(f"   Формат: {archive_format}")

            # Получаем информацию об аккаунтах
            accounts_info = self.get_archive_info(account_names, category)
            if not accounts_info:
                return {
                    'success': False,
                    'message': 'Не найдены аккаунты для архивации',
                    'archived_count': 0
                }

            # Создаем временную папку для архивации
            temp_folder = self.archive_base_path / archive_name
            temp_folder.mkdir(parents=True, exist_ok=True)

            # Копируем файлы аккаунтов
            copied_count = self._copy_account_files(accounts_info, temp_folder)

            # Создаем архив
            archive_path = self._create_archive(temp_folder, archive_name, archive_format)

            # Удаляем временную папку
            shutil.rmtree(temp_folder)

            logger.info(f"✅ Архивация завершена успешно")
            logger.info(f"   Архив создан: {archive_path}")
            logger.info(f"   Заархивировано: {copied_count} аккаунтов")

            return {
                'success': True,
                'message': f'Архив создан: {archive_path.name}',
                'archive_path': str(archive_path),
                'archived_count': copied_count,
                'archive_size': self._get_file_size(archive_path)
            }

        except Exception as e:
            logger.error(f"❌ Ошибка архивации: {e}")
            return {
                'success': False,
                'message': f'Ошибка архивации: {str(e)}',
                'archived_count': 0
            }

    def get_archive_info(self, account_names: List[str], category: str) -> List[Dict]:
        """Получает информацию об аккаунтах для архивации"""
        accounts_storage = self._get_accounts_storage(category)
        if not accounts_storage:
            return []

        accounts_info = []
        for account_name in account_names:
            if account_name in accounts_storage:
                account_data = accounts_storage[account_name]
                info = account_data.info

                accounts_info.append({
                    'name': account_name,
                    'full_name': info.get('full_name', '?'),
                    'phone': info.get('phone', '?'),
                    'status': account_data.status,
                    'category': category,
                    'session_file': str(account_data.account.session_path),
                    'json_file': str(account_data.account.json_path)
                })

        return accounts_info

    def _copy_account_files(self, accounts_info: List[Dict], temp_folder: Path) -> int:
        """Копирует файлы аккаунтов в временную папку"""
        copied_count = 0

        for account in accounts_info:
            try:
                session_src = Path(account['session_file'])
                json_src = Path(account['json_file'])

                # Копируем .session файл
                if session_src.exists():
                    session_dst = temp_folder / session_src.name
                    shutil.copy2(session_src, session_dst)
                    logger.debug(f"   📄 Скопирован: {session_src.name}")

                # Копируем .json файл
                if json_src.exists():
                    json_dst = temp_folder / json_src.name
                    shutil.copy2(json_src, json_dst)
                    logger.debug(f"   📄 Скопирован: {json_src.name}")

                copied_count += 1

            except Exception as e:
                logger.error(f"❌ Ошибка копирования {account['name']}: {e}")
                continue

        logger.info(f"📋 Скопировано файлов для {copied_count} аккаунтов")
        return copied_count

    def _create_archive(self, temp_folder: Path, archive_name: str, archive_format: str) -> Path:
        """Создает архив из временной папки"""
        archive_path = self.archive_base_path / f"{archive_name}.{archive_format}"

        if archive_format == "zip":
            self._create_zip_archive(temp_folder, archive_path)
        elif archive_format == "rar":
            self._create_rar_archive(temp_folder, archive_path)
        else:
            raise ValueError(f"Неподдерживаемый формат архива: {archive_format}")

        return archive_path

    def _create_zip_archive(self, source_folder: Path, archive_path: Path):
        """Создает ZIP архив"""
        logger.info(f"📦 Создаем ZIP архив: {archive_path.name}")

        # Убираем расширение для shutil.make_archive
        archive_base = archive_path.with_suffix('')
        shutil.make_archive(str(archive_base), 'zip', source_folder)

        logger.info(f"✅ ZIP архив создан")

    def _create_rar_archive(self, source_folder: Path, archive_path: Path):
        """Создает RAR архив"""
        logger.info(f"📦 Создаем RAR архив: {archive_path.name}")

        # Ищем WinRAR
        winrar_exe = self._find_winrar()
        if not winrar_exe:
            raise Exception("WinRAR не найден в системе")

        # Команда для создания RAR архива
        cmd = [
            str(winrar_exe),
            "a",  # Добавить в архив
            "-r",  # Рекурсивно
            "-ep1",  # Исключить базовый путь
            str(archive_path),
            str(source_folder / "*")
        ]

        logger.debug(f"   Команда WinRAR: {' '.join(cmd)}")

        result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(source_folder.parent))

        if result.returncode != 0:
            logger.error(f"❌ Ошибка WinRAR: {result.stderr}")
            raise Exception(f"Ошибка создания RAR архива: {result.stderr}")

        logger.info(f"✅ RAR архив создан")

    def _find_winrar(self) -> Path:
        """Находит исполняемый файл WinRAR"""
        winrar_paths = [
            Path(r"C:\Program Files\WinRAR\WinRAR.exe"),
            Path(r"C:\Program Files (x86)\WinRAR\WinRAR.exe"),
            Path(r"C:\Program Files\WinRAR\Rar.exe"),
            Path(r"C:\Program Files (x86)\WinRAR\Rar.exe")
        ]

        for path in winrar_paths:
            if path.exists():
                logger.debug(f"   Найден WinRAR: {path}")
                return path

        return None

    def _get_file_size(self, file_path: Path) -> str:
        """Получает размер файла в читаемом формате"""
        try:
            size = file_path.stat().st_size

            if size < 1024:
                return f"{size} B"
            elif size < 1024 * 1024:
                return f"{size / 1024:.1f} KB"
            elif size < 1024 * 1024 * 1024:
                return f"{size / (1024 * 1024):.1f} MB"
            else:
                return f"{size / (1024 * 1024 * 1024):.1f} GB"
        except:
            return "? KB"

    def _get_accounts_storage(self, category: str):
        """Получает правильное хранилище аккаунтов"""
        if category == "traffic":
            return self.manager.traffic_accounts
        elif category == "sales":
            return self.manager.sales_accounts
        else:
            logger.error(f"❌ Неизвестная категория: {category}")
            return None

    def check_winrar_available(self) -> bool:
        """Проверяет доступность WinRAR"""
        return self._find_winrar() is not None

    def get_archive_list(self) -> List[Dict]:
        """Получает список созданных архивов"""
        archives = []

        try:
            for archive_file in self.archive_base_path.glob("*"):
                if archive_file.is_file() and archive_file.suffix.lower() in ['.zip', '.rar']:
                    archives.append({
                        'name': archive_file.name,
                        'path': str(archive_file),
                        'size': self._get_file_size(archive_file),
                        'created': datetime.fromtimestamp(archive_file.stat().st_mtime),
                        'format': archive_file.suffix.lower()[1:]  # Убираем точку
                    })
        except Exception as e:
            logger.error(f"❌ Ошибка получения списка архивов: {e}")

        # Сортируем по дате создания (новые сначала)
        archives.sort(key=lambda x: x['created'], reverse=True)

        return archives