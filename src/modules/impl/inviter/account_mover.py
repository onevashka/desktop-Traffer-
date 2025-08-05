# src/modules/impl/inviter/account_mover.py
"""
Простая система перемещения аккаунтов
Перемещает session + json файлы в указанные папки
"""

import shutil
from pathlib import Path
from loguru import logger


class AccountMover:
    """Простой класс для перемещения аккаунтов в папки"""

    def __init__(self, profile_folder: Path):
        self.profile_folder = Path(profile_folder)

        # Папки для проблемных аккаунтов
        self.folders = {
            'frozen': self.profile_folder / "Замороженные",
            'dead': self.profile_folder / "Мертвые",
            'connection_failed': self.profile_folder / "Не_удалось_подключиться",
            'unauthorized': self.profile_folder / "Не_авторизованы"
        }

        # ДОБАВЛЕНО: Отслеживание перемещенных аккаунтов
        self.moved_accounts = set()

        # Создаем папки
        for folder in self.folders.values():
            folder.mkdir(parents=True, exist_ok=True)

    def move_account(self, account_name: str, folder_type: str) -> bool:
        """
        Перемещает аккаунт в указанную папку

        Args:
            account_name: Имя аккаунта
            folder_type: Тип папки ('frozen', 'dead', 'connection_failed', 'unauthorized')

        Returns:
            bool: Успешность перемещения
        """
        try:
            if folder_type not in self.folders:
                logger.error(f"❌ Неизвестный тип папки: {folder_type}")
                return False

            target_folder = self.folders[folder_type]

            # Ищем файлы аккаунта
            session_file = self.profile_folder / f"{account_name}.session"
            json_file = self.profile_folder / f"{account_name}.json"

            # Также ищем в папке Админы
            admin_folder = self.profile_folder / "Админы"
            admin_session = admin_folder / f"{account_name}.session"
            admin_json = admin_folder / f"{account_name}.json"

            files_to_move = []

            # Проверяем основную папку
            if session_file.exists():
                files_to_move.append(session_file)
            if json_file.exists():
                files_to_move.append(json_file)

            # Проверяем папку админов
            if admin_session.exists():
                files_to_move.append(admin_session)
            if admin_json.exists():
                files_to_move.append(admin_json)

            if not files_to_move:
                logger.warning(f"⚠️ Файлы аккаунта {account_name} не найдены")
                return False

            # Перемещаем файлы
            for file_path in files_to_move:
                target_path = target_folder / file_path.name
                shutil.move(str(file_path), str(target_path))
                logger.debug(f"📁 {file_path.name} → {folder_type}")

            logger.success(f"✅ Аккаунт {account_name} перемещен в папку '{folder_type}' ({len(files_to_move)} файлов)")
            return True

        except Exception as e:
            logger.error(f"❌ Ошибка перемещения аккаунта {account_name}: {e}")
            return False

    def is_account_moved(self, account_name: str) -> bool:
        """Проверяет перемещен ли аккаунт"""
        return account_name in self.moved_accounts