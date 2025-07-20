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
        Архивирует аккаунты с ПЕРЕМЕЩЕНИЕМ файлов (не копированием)

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

            # Создаем папку для архивации
            archive_folder = self.archive_base_path / archive_name
            archive_folder.mkdir(parents=True, exist_ok=True)

            # ИЗМЕНЕНО: Перемещаем файлы аккаунтов (не копируем)
            moved_count = self._move_account_files(accounts_info, archive_folder, category)

            if moved_count == 0:
                # Если не удалось переместить файлы, удаляем пустую папку
                if archive_folder.exists():
                    shutil.rmtree(archive_folder)
                return {
                    'success': False,
                    'message': 'Не удалось переместить файлы для архивации',
                    'archived_count': 0
                }

            # Создаем архив
            archive_path = self._create_archive(archive_folder, archive_name, archive_format)

            # Удаляем папку после архивации
            shutil.rmtree(archive_folder)

            logger.info(f"✅ Архивация завершена успешно")
            logger.info(f"   Архив создан: {archive_path}")
            logger.info(f"   Заархивировано: {moved_count} аккаунтов")

            return {
                'success': True,
                'message': f'Архив создан: {archive_path.name}',
                'archive_path': str(archive_path),
                'archived_count': moved_count,
                'archive_size': self._get_file_size(archive_path),
                'moved_accounts': account_names[:moved_count]  # Добавляем для обновления данных
            }

        except Exception as e:
            logger.error(f"❌ Ошибка архивации: {e}")
            # В случае ошибки пытаемся восстановить файлы
            self._rollback_move_operation(accounts_info, archive_folder, category)
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

    def _move_account_files(self, accounts_info: List[Dict], archive_folder: Path, category: str) -> int:
        """Перемещает файлы аккаунтов в папку для архивации"""
        moved_count = 0
        moved_files = []  # Для отката в случае ошибки

        accounts_storage = self._get_accounts_storage(category)

        for account in accounts_info:
            try:
                session_src = Path(account['session_file'])
                json_src = Path(account['json_file'])

                # Перемещаем .session файл
                if session_src.exists():
                    session_dst = archive_folder / session_src.name
                    shutil.move(str(session_src), str(session_dst))
                    moved_files.append((session_dst, session_src))
                    logger.debug(f"   📄 Перемещен: {session_src.name}")

                # Перемещаем .json файл
                if json_src.exists():
                    json_dst = archive_folder / json_src.name
                    shutil.move(str(json_src), str(json_dst))
                    moved_files.append((json_dst, json_src))
                    logger.debug(f"   📄 Перемещен: {json_src.name}")

                # Удаляем аккаунт из хранилища менеджера
                account_name = account['name']
                if account_name in accounts_storage:
                    del accounts_storage[account_name]
                    logger.debug(f"   🗑️ Удален из хранилища: {account_name}")

                moved_count += 1

            except Exception as e:
                logger.error(f"❌ Ошибка перемещения {account['name']}: {e}")
                # В случае ошибки пытаемся откатить уже перемещенные файлы
                self._rollback_moved_files(moved_files)
                break

        logger.info(f"📋 Перемещено файлов для {moved_count} аккаунтов")
        return moved_count

    def _rollback_moved_files(self, moved_files: List[tuple]):
        """Откатывает перемещенные файлы в случае ошибки"""
        logger.warning("🔄 Откатываем перемещенные файлы...")

        for dst_path, src_path in reversed(moved_files):
            try:
                if dst_path.exists():
                    shutil.move(str(dst_path), str(src_path))
                    logger.debug(f"   ↩️ Восстановлен: {src_path.name}")
            except Exception as e:
                logger.error(f"❌ Ошибка отката {dst_path.name}: {e}")

    def _rollback_move_operation(self, accounts_info: List[Dict], archive_folder: Path, category: str):
        """Откатывает операцию перемещения при критической ошибке"""
        if not archive_folder.exists():
            return

        logger.warning("🔄 Откатываем операцию архивации...")

        for account in accounts_info:
            try:
                account_name = account['name']
                session_src = archive_folder / f"{account_name}.session"
                json_src = archive_folder / f"{account_name}.json"

                # Восстанавливаем файлы в исходное место
                if session_src.exists():
                    original_session = Path(account['session_file'])
                    shutil.move(str(session_src), str(original_session))

                if json_src.exists():
                    original_json = Path(account['json_file'])
                    shutil.move(str(json_src), str(original_json))

                logger.debug(f"   ↩️ Восстановлен аккаунт: {account_name}")

            except Exception as e:
                logger.error(f"❌ Ошибка отката аккаунта {account['name']}: {e}")

        # Удаляем папку архивации
        try:
            if archive_folder.exists():
                shutil.rmtree(archive_folder)
        except Exception as e:
            logger.error(f"❌ Ошибка удаления папки отката: {e}")

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
        """Создает RAR архив - ОКОНЧАТЕЛЬНО ИСПРАВЛЕННАЯ ВЕРСИЯ"""
        logger.info(f"📦 Создаем RAR архив: {archive_path.name}")

        # Ищем WinRAR
        winrar_exe = self._find_winrar()
        if not winrar_exe:
            raise Exception("WinRAR не найден в системе")

        # Проверяем что исходная папка существует и не пуста
        if not source_folder.exists():
            raise Exception(f"Исходная папка не существует: {source_folder}")

        files_in_folder = list(source_folder.glob("*"))
        if not files_in_folder:
            raise Exception(f"Исходная папка пуста: {source_folder}")

        logger.debug(f"   Файлы в папке: {[f.name for f in files_in_folder]}")

        # Создаем абсолютные пути
        abs_source_folder = source_folder.resolve()
        abs_archive_path = archive_path.resolve()

        # ИСПРАВЛЕНО: Упрощенная команда WinRAR
        cmd = [
            str(winrar_exe),
            "a",  # Добавить в архив
            "-r",  # Рекурсивно
            str(abs_archive_path),  # Путь к создаваемому архиву (абсолютный)
            "*"  # Все файлы из текущей папки
        ]

        logger.debug(f"   Команда WinRAR: {' '.join(cmd)}")
        logger.debug(f"   Рабочая папка: {abs_source_folder}")
        logger.debug(f"   Целевой архив: {abs_archive_path}")

        # ИСПРАВЛЕНО: Запускаем из папки с файлами
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(abs_source_folder),  # Запускаем ИЗ папки с файлами
            shell=False,
            encoding='utf-8',
            errors='ignore'
        )

        logger.debug(f"   Код возврата WinRAR: {result.returncode}")
        if result.stdout:
            logger.debug(f"   Вывод WinRAR: {result.stdout}")
        if result.stderr:
            logger.debug(f"   Ошибки WinRAR: {result.stderr}")

        # WinRAR коды ошибок:
        # 0 = успех
        # 1 = предупреждение (но архив создан)
        # 2-255 = различные ошибки
        if result.returncode > 1:
            error_msg = self._get_winrar_error_message(result.returncode)
            logger.error(f"❌ Ошибка WinRAR (код {result.returncode}): {error_msg}")
            if result.stderr:
                logger.error(f"❌ Детали ошибки: {result.stderr}")
            if result.stdout:
                logger.error(f"❌ Вывод: {result.stdout}")
            raise Exception(f"Ошибка создания RAR архива. {error_msg}")

        # Проверяем что архив действительно создался
        if not abs_archive_path.exists():
            raise Exception("RAR архив не был создан, файл отсутствует")

        # Проверяем размер архива
        archive_size = abs_archive_path.stat().st_size
        if archive_size == 0:
            raise Exception("RAR архив создан, но он пустой")

        logger.info(f"✅ RAR архив создан успешно (размер: {self._get_file_size(abs_archive_path)})")

    def _get_winrar_error_message(self, error_code: int) -> str:
        """Возвращает описание ошибки WinRAR по коду"""
        error_messages = {
            2: "Фатальная ошибка",
            3: "Ошибка CRC",
            4: "Ошибка блокировки архива",
            5: "Ошибка записи",
            6: "Ошибка открытия файла",
            7: "Неправильная команда",
            8: "Недостаточно памяти",
            9: "Файл не найден",
            10: "Недостаточно места на диске",
            11: "Превышен лимит файлов",
            255: "Прервано пользователем"
        }

        return error_messages.get(error_code, f"Неизвестная ошибка (код {error_code})")

    def _find_winrar(self) -> Path:
        """Находит исполняемый файл WinRAR - УЛУЧШЕННАЯ ВЕРСИЯ"""
        # Список возможных путей к WinRAR (включая консольную версию)
        winrar_paths = [
            Path(r"C:\Program Files\WinRAR\Rar.exe"),  # Консольная версия (приоритет)
            Path(r"C:\Program Files (x86)\WinRAR\Rar.exe"),
            Path(r"C:\Program Files\WinRAR\WinRAR.exe"),  # GUI версия
            Path(r"C:\Program Files (x86)\WinRAR\WinRAR.exe")
        ]

        for path in winrar_paths:
            if path.exists():
                logger.debug(f"   ✅ Найден WinRAR: {path}")
                return path

        # Дополнительно ищем в PATH
        try:
            # Сначала ищем консольную версию
            for exe_name in ["rar.exe", "winrar.exe"]:
                result = subprocess.run(["where", exe_name], capture_output=True, text=True, shell=True)
                if result.returncode == 0:
                    winrar_path = Path(result.stdout.strip().split('\n')[0])
                    if winrar_path.exists():
                        logger.debug(f"   ✅ Найден WinRAR в PATH: {winrar_path}")
                        return winrar_path
        except:
            pass

        logger.warning("❌ WinRAR не найден в системе")
        return None

    def check_winrar_available(self) -> bool:
        """Проверяет доступность WinRAR - УЛУЧШЕННАЯ ВЕРСИЯ"""
        winrar_path = self._find_winrar()
        if winrar_path:
            # Дополнительно проверяем что WinRAR запускается
            try:
                result = subprocess.run([str(winrar_path)], capture_output=True, timeout=5)
                # WinRAR обычно возвращает код 0 при запуске без параметров
                logger.debug(f"   WinRAR тест: код {result.returncode}")
                return True
            except subprocess.TimeoutExpired:
                # Таймаут тоже означает что WinRAR запустился
                return True
            except Exception as e:
                logger.warning(f"   WinRAR тест провален: {e}")
                return False
        return False

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