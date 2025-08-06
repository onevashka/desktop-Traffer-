"""
ИСПРАВЛЕННАЯ система перемещения аккаунтов
Правильный порядок: отключение → перемещение → освобождение
ДОБАВЛЕНО: Новые папки для специфичных типов ошибок
"""

import shutil
from pathlib import Path
from loguru import logger
from typing import List


class AccountMover:
    """Исправленный класс для перемещения аккаунтов с новыми папками"""

    def __init__(self, profile_folder: Path):
        self.profile_folder = Path(profile_folder)

        # Импортируем глобальные пути
        from paths import WORK_ACCOUNTS_TRAFFER_FOLDER, WORK_TRAFFER_FOLDER

        # Основная рабочая папка
        self.main_accounts_folder = WORK_ACCOUNTS_TRAFFER_FOLDER

        # Папки для проблемных аккаунтов
        self.folders = {
            'frozen': WORK_TRAFFER_FOLDER / "Замороженные",
            'dead': WORK_TRAFFER_FOLDER / "Мертвые",
            'connection_failed': WORK_TRAFFER_FOLDER / "Не_удалось_подключиться",
            'unauthorized': WORK_TRAFFER_FOLDER / "Не_авторизованы",
            # НОВЫЕ ПАПКИ для специфичных ошибок
            'writeoff': WORK_TRAFFER_FOLDER / "Списанные",
            'spam_block': WORK_TRAFFER_FOLDER / "Спам_блок",
            'block_invite': WORK_TRAFFER_FOLDER / "Блок_инвайтов",
            "finished" : WORK_TRAFFER_FOLDER / "Успешно отработанные"
        }

        # Отслеживание перемещенных аккаунтов
        self.moved_accounts = set()

        # Создаем все папки (включая новые)
        self._create_folders()

        logger.debug(f"📁 AccountMover инициализирован для: {profile_folder.name}")

    def _create_folders(self):
        """Создает все необходимые папки для перемещения"""
        created_folders = []

        for folder_type, folder_path in self.folders.items():
            try:
                if not folder_path.exists():
                    folder_path.mkdir(parents=True, exist_ok=True)
                    created_folders.append(folder_type)
                    logger.debug(f"📁 Создана папка: {folder_path}")
            except Exception as e:
                logger.error(f"❌ Ошибка создания папки {folder_type}: {e}")

        if created_folders:
            logger.info(f"📁 Созданы папки для перемещения: {', '.join(created_folders)}")

    def move_account(self, account_name: str, folder_type: str) -> bool:
        """
        Перемещает аккаунт в указанную папку
        ВАЖНО: Вызывать только ПОСЛЕ отключения клиента!
        """
        try:
            if folder_type not in self.folders:
                logger.error(f"❌ Неизвестный тип папки: {folder_type}")
                logger.info(f"📋 Доступные типы: {', '.join(self.folders.keys())}")
                return False

            target_folder = self.folders[folder_type]

            # Убеждаемся что папка существует
            if not target_folder.exists():
                try:
                    target_folder.mkdir(parents=True, exist_ok=True)
                    logger.info(f"📁 Создана папка: {target_folder}")
                except Exception as e:
                    logger.error(f"❌ Не удалось создать папку {target_folder}: {e}")
                    return False

            # Ищем файлы аккаунта в возможных локациях
            files_to_move = self._find_account_files(account_name)

            if not files_to_move:
                logger.warning(f"⚠️ Файлы аккаунта {account_name} не найдены")
                # Все равно помечаем как перемещенный
                self.moved_accounts.add(account_name)
                return False

            # Перемещаем файлы
            moved_count = 0
            for file_path in files_to_move:
                try:
                    target_path = target_folder / file_path.name

                    # Если файл уже существует в целевой папке - удаляем старый
                    if target_path.exists():
                        target_path.unlink()
                        logger.debug(f"🗑️ Удален существующий файл: {target_path.name}")

                    shutil.move(str(file_path), str(target_path))
                    moved_count += 1
                    logger.debug(f"📁 {file_path.name} → {self._get_folder_display_name(folder_type)}")

                except Exception as move_error:
                    logger.error(f"❌ Ошибка перемещения {file_path.name}: {move_error}")

            # Помечаем как перемещенный
            self.moved_accounts.add(account_name)

            if moved_count > 0:
                folder_display = self._get_folder_display_name(folder_type)
                logger.success(f"✅ Аккаунт {account_name} перемещен в '{folder_display}' ({moved_count} файлов)")
                return True
            else:
                logger.error(f"❌ Не удалось переместить файлы для {account_name}")
                return False

        except Exception as e:
            logger.error(f"❌ Ошибка перемещения аккаунта {account_name}: {e}")
            # Все равно помечаем как перемещенный чтобы избежать повторного использования
            self.moved_accounts.add(account_name)
            return False

    def _get_folder_display_name(self, folder_type: str) -> str:
        """Возвращает красивое название папки для логов"""
        display_names = {
            'frozen': 'Замороженные',
            'dead': 'Мертвые',
            'connection_failed': 'Не удалось подключиться',
            'unauthorized': 'Не авторизованы',
            'writeoff': 'Списанные',
            'spam_block': 'Спам-блок',
            'block_invite': 'Блок инвайтов'
        }
        return display_names.get(folder_type, folder_type)

    def _find_account_files(self, account_name: str) -> List[Path]:
        """Находит все файлы аккаунта в возможных папках"""
        files = []

        # Поиск в основной рабочей папке
        work_session = self.main_accounts_folder / f"{account_name}.session"
        work_json = self.main_accounts_folder / f"{account_name}.json"

        if work_session.exists():
            files.append(work_session)
        if work_json.exists():
            files.append(work_json)

        # Поиск в папке админов
        admin_folder = self.profile_folder / "Админы"
        admin_session = admin_folder / f"{account_name}.session"
        admin_json = admin_folder / f"{account_name}.json"

        if admin_session.exists():
            files.append(admin_session)
        if admin_json.exists():
            files.append(admin_json)

        # Поиск в папке профиля (на всякий случай)
        profile_session = self.profile_folder / f"{account_name}.session"
        profile_json = self.profile_folder / f"{account_name}.json"

        if profile_session.exists():
            files.append(profile_session)
        if profile_json.exists():
            files.append(profile_json)

        return files

    def is_account_moved(self, account_name: str) -> bool:
        """Проверяет перемещен ли аккаунт"""
        return account_name in self.moved_accounts

    def get_moved_accounts_count(self) -> int:
        """Возвращает количество перемещенных аккаунтов"""
        return len(self.moved_accounts)

    def get_moved_accounts_by_type(self) -> dict:
        """Возвращает статистику перемещенных аккаунтов по типам"""
        stats = {}

        for folder_type, folder_path in self.folders.items():
            if folder_path.exists():
                session_files = list(folder_path.glob("*.session"))
                stats[self._get_folder_display_name(folder_type)] = len(session_files)
            else:
                stats[self._get_folder_display_name(folder_type)] = 0

        return stats

    def reset_moved_accounts(self):
        """Сбрасывает список перемещенных аккаунтов (для отладки)"""
        self.moved_accounts.clear()
        logger.info("🔄 Список перемещенных аккаунтов сброшен")

    def get_available_folder_types(self) -> List[str]:
        """Возвращает список доступных типов папок"""
        return list(self.folders.keys())

    def check_folders_exist(self) -> dict:
        """Проверяет существование всех папок"""
        status = {}
        for folder_type, folder_path in self.folders.items():
            status[folder_type] = {
                'exists': folder_path.exists(),
                'path': str(folder_path),
                'display_name': self._get_folder_display_name(folder_type)
            }
        return status