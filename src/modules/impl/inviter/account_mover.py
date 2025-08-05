files_to_move = []

# ИСПРАВЛЕНО: Проверяем основную рабочую папку
"""
Простая система перемещения аккаунтов
Перемещает session + json файлы в указанные папки
"""

import shutil
from pathlib import Path
from loguru import logger
from paths import WORK_ACCOUNTS_TRAFFER_FOLDER


class AccountMover:
    """Простой класс для перемещения аккаунтов в папки"""

    def __init__(self, profile_folder: Path):
        self.profile_folder = Path(profile_folder)

        # ИСПРАВЛЕНО: Импортируем глобальные пути
        from paths import WORK_ACCOUNTS_TRAFFER_FOLDER, WORK_TRAFFER_FOLDER

        # Основная рабочая папка для аккаунтов (общая для всех)
        self.main_accounts_folder = WORK_ACCOUNTS_TRAFFER_FOLDER

        # Папки для проблемных аккаунтов (в общей папке "Для работы")
        self.folders = {
            'frozen': WORK_TRAFFER_FOLDER / "Замороженные",
            'dead': WORK_TRAFFER_FOLDER / "Мертвые",
            'connection_failed': WORK_TRAFFER_FOLDER / "Не_удалось_подключиться",
            'unauthorized': WORK_TRAFFER_FOLDER / "Не_авторизованы"
        }

        # Отслеживание перемещенных аккаунтов
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

            # ИСПРАВЛЕНО: Ищем файлы аккаунта в правильных папках
            # Основная рабочая папка - "Для работы/Аккаунты"
            work_folder = WORK_ACCOUNTS_TRAFFER_FOLDER
            session_file = work_folder / f"{account_name}.session"
            json_file = work_folder / f"{account_name}.json"

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
                logger.warning(f"⚠️ Файлы аккаунта {account_name} не найдены нигде")
                logger.debug(f"   Основной поиск: {self.main_accounts_folder}")
                logger.debug(f"   Админы: {admin_folder}")

                # ИСПРАВЛЕНО: Все равно помечаем как перемещенный чтобы избежать повторного использования
                self.moved_accounts.add(account_name)
                return False

            # Перемещаем файлы
            moved_files = []
            for file_path in files_to_move:
                try:
                    target_path = target_folder / file_path.name
                    shutil.move(str(file_path), str(target_path))
                    moved_files.append(file_path.name)
                    logger.debug(f"📁 {file_path.name} → {folder_type}")
                except Exception as move_error:
                    logger.error(f"❌ Ошибка перемещения файла {file_path}: {move_error}")

            # ИСПРАВЛЕНО: Обязательно добавляем в moved_accounts
            self.moved_accounts.add(account_name)

            if moved_files:
                logger.success(
                    f"✅ Аккаунт {account_name} перемещен в папку '{folder_type}' ({len(moved_files)} файлов)")
                return True
            else:
                logger.error(f"❌ Не удалось переместить ни одного файла для {account_name}")
                return False

        except Exception as e:
            logger.error(f"❌ Ошибка перемещения аккаунта {account_name}: {e}")
            # ИСПРАВЛЕНО: Даже при ошибке помечаем как перемещенный
            self.moved_accounts.add(account_name)
            return False

    def is_account_moved(self, account_name: str) -> bool:
        """Проверяет перемещен ли аккаунт"""
        return account_name in self.moved_accounts