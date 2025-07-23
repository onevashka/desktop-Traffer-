# src/accounts/services/folder_service.py
"""
Сервис папок - отвечает за работу с папками, путями и метаданными
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple
from loguru import logger


class FolderService:
    """Сервис для работы с папками аккаунтов"""

    def __init__(self, traffic_folders: Dict[str, Path], sales_folders: Dict[str, Path]):
        self.traffic_folders = traffic_folders
        self.sales_folders = sales_folders
        logger.debug("📁 FolderService инициализирован")

    def get_default_status(self, category: str) -> str:
        """
        Возвращает статус по умолчанию для категории

        Args:
            category: "traffic" или "sales"

        Returns:
            str: Статус по умолчанию
        """
        if category == "traffic":
            return "active"  # Показываем активные аккаунты
        elif category == "sales":
            return "registration"  # Показываем регистрационные аккаунты
        else:
            return "active"

    def get_status_display_name(self, category: str, status: str) -> str:
        """
        Возвращает человекочитаемое название статуса

        Args:
            category: "traffic" или "sales"
            status: Статус папки

        Returns:
            str: Отображаемое название
        """
        display_names = {
            "traffic": {
                "active": "Активные аккаунты",
                "dead": "Мертвые аккаунты",
                "frozen": "Замороженные аккаунты",
                "invalid": "Неверный формат"
            },
            "sales": {
                "registration": "Регистрационные аккаунты",
                "ready_tdata": "TData готовые",
                "ready_sessions": "Session+JSON готовые",
                "middle": "Средние аккаунты",
                "dead": "Мертвые аккаунты",
                "frozen": "Замороженные аккаунты",
                "invalid": "Неверный формат"
            }
        }

        return display_names.get(category, {}).get(status, f"Аккаунты ({status})")

    def get_folder_path(self, category: str, status: str) -> Optional[Path]:
        """
        Получает путь к папке по категории и статусу

        Args:
            category: "traffic" или "sales"
            status: Статус папки

        Returns:
            Path или None если не найдено
        """
        if category == "traffic":
            return self.traffic_folders.get(status)
        elif category == "sales":
            return self.sales_folders.get(status)
        else:
            return None

    def get_all_folders(self) -> Dict[str, Dict[str, Path]]:
        """
        Возвращает все папки

        Returns:
            Dict: {"traffic": {...}, "sales": {...}}
        """
        return {
            "traffic": self.traffic_folders.copy(),
            "sales": self.sales_folders.copy()
        }

    def get_category_folders(self, category: str) -> Dict[str, Path]:
        """
        Получает папки конкретной категории

        Args:
            category: "traffic" или "sales"

        Returns:
            Dict[str, Path]: Папки категории
        """
        if category == "traffic":
            return self.traffic_folders.copy()
        elif category == "sales":
            return self.sales_folders.copy()
        else:
            return {}

    def ensure_folders_exist(self) -> Dict[str, bool]:
        """
        Проверяет и создает папки если они не существуют

        Returns:
            Dict[str, bool]: Результат создания папок
        """
        results = {}

        # Проверяем папки трафика
        for status, folder_path in self.traffic_folders.items():
            try:
                folder_path.mkdir(parents=True, exist_ok=True)
                results[f"traffic_{status}"] = True
                logger.debug(f"✅ Папка проверена/создана: {folder_path}")
            except Exception as e:
                results[f"traffic_{status}"] = False
                logger.error(f"❌ Ошибка создания папки {folder_path}: {e}")

        # Проверяем папки продаж
        for status, folder_path in self.sales_folders.items():
            try:
                folder_path.mkdir(parents=True, exist_ok=True)
                results[f"sales_{status}"] = True
                logger.debug(f"✅ Папка проверена/создана: {folder_path}")
            except Exception as e:
                results[f"sales_{status}"] = False
                logger.error(f"❌ Ошибка создания папки {folder_path}: {e}")

        return results

    def get_folder_info(self, category: str, status: str) -> Dict:
        """
        Получает подробную информацию о папке

        Args:
            category: "traffic" или "sales"
            status: Статус папки

        Returns:
            Dict: Информация о папке
        """
        folder_path = self.get_folder_path(category, status)
        if not folder_path:
            return {}

        try:
            info = {
                'path': str(folder_path),
                'exists': folder_path.exists(),
                'is_directory': folder_path.is_dir() if folder_path.exists() else False,
                'readable': folder_path.exists() and os.access(folder_path, os.R_OK),
                'writable': folder_path.exists() and os.access(folder_path, os.W_OK),
                'session_files': 0,
                'json_files': 0,
                'other_files': 0,
                'total_size': 0
            }

            if folder_path.exists() and folder_path.is_dir():
                session_files = list(folder_path.glob("*.session"))
                json_files = list(folder_path.glob("*.json"))
                all_files = list(folder_path.iterdir())

                info['session_files'] = len(session_files)
                info['json_files'] = len(json_files)
                info['other_files'] = len(all_files) - len(session_files) - len(json_files)

                # Подсчитываем размер
                total_size = 0
                for file_path in all_files:
                    if file_path.is_file():
                        try:
                            total_size += file_path.stat().st_size
                        except:
                            pass
                info['total_size'] = total_size

        except Exception as e:
            logger.error(f"❌ Ошибка получения информации о папке {folder_path}: {e}")
            info = {'error': str(e)}

        return info

    def get_move_destinations(self, current_category: str, current_status: str) -> List[Dict]:
        """
        Получает список доступных папок для перемещения

        Args:
            current_category: Текущая категория
            current_status: Текущий статус

        Returns:
            List[Dict]: Список доступных назначений
        """
        destinations = []

        # Добавляем папки трафика
        for status, folder_path in self.traffic_folders.items():
            if not (current_category == "traffic" and current_status == status):
                destinations.append({
                    'category': 'traffic',
                    'status': status,
                    'display_name': f"🚀 Трафик → {self._get_status_display_short(status)}",
                    'folder_path': folder_path
                })

        # Добавляем папки продаж
        for status, folder_path in self.sales_folders.items():
            if not (current_category == "sales" and current_status == status):
                destinations.append({
                    'category': 'sales',
                    'status': status,
                    'display_name': f"💰 Продажи → {self._get_status_display_short(status)}",
                    'folder_path': folder_path
                })

        return destinations

    def validate_folder_structure(self) -> Dict[str, List[str]]:
        """
        Проверяет корректность структуры папок

        Returns:
            Dict: {"errors": [...], "warnings": [...], "info": [...]}
        """
        errors = []
        warnings = []
        info = []

        all_folders = {**self.traffic_folders, **self.sales_folders}

        for status, folder_path in all_folders.items():
            try:
                if not folder_path.exists():
                    warnings.append(f"Папка {status} не существует: {folder_path}")
                    continue

                if not folder_path.is_dir():
                    errors.append(f"Путь {status} не является папкой: {folder_path}")
                    continue

                # Проверяем права доступа
                import os
                if not os.access(folder_path, os.R_OK):
                    errors.append(f"Нет прав чтения для папки {status}: {folder_path}")

                if not os.access(folder_path, os.W_OK):
                    warnings.append(f"Нет прав записи для папки {status}: {folder_path}")

                # Проверяем содержимое
                files = list(folder_path.iterdir())
                session_files = [f for f in files if f.suffix == '.session']
                json_files = [f for f in files if f.suffix == '.json']

                if len(session_files) == 0:
                    info.append(f"Папка {status} пуста")
                else:
                    # Проверяем парность session/json файлов
                    session_names = {f.stem for f in session_files}
                    json_names = {f.stem for f in json_files}

                    missing_json = session_names - json_names
                    if missing_json:
                        warnings.append(f"В папке {status} отсутствуют JSON файлы для: {', '.join(missing_json)}")

                    orphan_json = json_names - session_names
                    if orphan_json:
                        warnings.append(f"В папке {status} JSON файлы без session: {', '.join(orphan_json)}")

            except Exception as e:
                errors.append(f"Ошибка проверки папки {status}: {e}")

        return {
            "errors": errors,
            "warnings": warnings,
            "info": info
        }

    def _get_status_display_short(self, status: str) -> str:
        """Получает короткое отображаемое имя статуса"""
        short_names = {
            "active": "Активные",
            "dead": "Мертвые",
            "frozen": "Замороженные",
            "invalid": "Неверный формат",
            "registration": "Регистрация",
            "ready_tdata": "TData готовые",
            "ready_sessions": "Session готовые",
            "middle": "Средние"
        }
        return short_names.get(status, status)