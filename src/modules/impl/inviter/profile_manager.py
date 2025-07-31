# src/modules/impl/inviter/profile_manager.py
"""
Менеджер профилей инвайтера - управление профилями и их конфигурациями
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
from loguru import logger
from datetime import datetime

from paths import WORK_INVITER_FOLDER


class InviterProfileManager:
    """Менеджер профилей инвайтера"""

    def __init__(self):
        self.base_folder = WORK_INVITER_FOLDER
        self.base_folder.mkdir(parents=True, exist_ok=True)
        self.profiles: Dict[str, Dict] = {}
        logger.debug("📨 InviterProfileManager инициализирован")

    def create_profile(self, profile_name: str, initial_settings: Dict = None) -> Dict[str, any]:
        """
        Создает новый профиль инвайтера со всей структурой

        Args:
            profile_name: Название профиля
            initial_settings: Начальные настройки

        Returns:
            Dict с результатом операции
        """
        try:
            # Валидация имени
            if not profile_name or not profile_name.strip():
                return {'success': False, 'message': 'Название профиля не может быть пустым'}

            # Очищаем название от недопустимых символов
            clean_name = self._sanitize_folder_name(profile_name.strip())
            if not clean_name:
                return {'success': False, 'message': 'Недопустимое название профиля'}

            # Проверяем что профиль не существует
            profile_folder = self.base_folder / clean_name
            if profile_folder.exists():
                return {'success': False, 'message': f'Профиль "{clean_name}" уже существует'}

            logger.info(f"📨 Создаем профиль инвайтера: {clean_name}")

            # Создаем структуру профиля
            self._create_profile_structure(profile_folder)

            # Создаем конфигурацию
            config = self._create_default_config(clean_name, initial_settings)
            self._save_config(profile_folder, config)

            # Создаем пустые базы данных
            self._create_empty_databases(profile_folder)

            # Загружаем в память
            profile_data = {
                'name': clean_name,
                'folder_path': str(profile_folder),
                'config': config,
                'users_list': [],
                'chats_list': [],
                'is_running': False,
                'created_at': datetime.now().isoformat()
            }

            self.profiles[clean_name] = profile_data

            logger.info(f"✅ Профиль {clean_name} создан успешно")

            return {
                'success': True,
                'message': f'Профиль "{clean_name}" создан успешно',
                'profile_name': clean_name,
                'profile_path': str(profile_folder),
                'profile_data': profile_data
            }

        except Exception as e:
            logger.error(f"❌ Ошибка создания профиля {profile_name}: {e}")
            return {'success': False, 'message': f'Ошибка создания профиля: {str(e)}'}

    def load_all_profiles(self) -> Dict[str, Dict]:
        """Загружает все существующие профили"""
        try:
            self.profiles.clear()

            if not self.base_folder.exists():
                logger.info("📨 Папка инвайтера не существует, создаем...")
                self.base_folder.mkdir(parents=True, exist_ok=True)
                return {}

            # Сканируем папки профилей
            for profile_folder in self.base_folder.iterdir():
                if profile_folder.is_dir() and self._is_valid_profile(profile_folder):
                    profile_data = self._load_profile(profile_folder)
                    if profile_data:
                        self.profiles[profile_data['name']] = profile_data
                        logger.debug(f"📨 Профиль загружен: {profile_data['name']}")

            logger.info(f"✅ Загружено профилей: {len(self.profiles)}")
            return self.profiles

        except Exception as e:
            logger.error(f"❌ Ошибка загрузки профилей: {e}")
            return {}

    def get_profile(self, profile_name: str) -> Optional[Dict]:
        """Получает профиль по имени"""
        return self.profiles.get(profile_name)

    def get_all_profiles(self) -> List[Dict]:
        """Получает список всех профилей для GUI"""
        return list(self.profiles.values())

    def delete_profile(self, profile_name: str) -> Dict[str, any]:
        """Удаляет профиль"""
        try:
            if profile_name not in self.profiles:
                return {'success': False, 'message': f'Профиль "{profile_name}" не найден'}

            profile_data = self.profiles[profile_name]
            profile_folder = Path(profile_data['folder_path'])

            # Удаляем папку профиля
            import shutil
            if profile_folder.exists():
                shutil.rmtree(profile_folder)

            # Удаляем из памяти
            del self.profiles[profile_name]

            logger.info(f"🗑️ Профиль удален: {profile_name}")
            return {'success': True, 'message': f'Профиль "{profile_name}" удален'}

        except Exception as e:
            logger.error(f"❌ Ошибка удаления профиля {profile_name}: {e}")
            return {'success': False, 'message': f'Ошибка удаления: {str(e)}'}

    def update_users_database(self, profile_name: str, users_list: List[str]) -> bool:
        """Обновляет базу пользователей"""
        try:
            if profile_name not in self.profiles:
                logger.error(f"❌ Профиль не найден: {profile_name}")
                return False

            profile_data = self.profiles[profile_name]
            profile_folder = Path(profile_data['folder_path'])

            # Сохраняем в файл
            self._save_users_database(profile_folder, users_list)

            # Обновляем в памяти
            profile_data['users_list'] = users_list

            logger.info(f"📝 База пользователей обновлена для {profile_name}: {len(users_list)} пользователей")
            return True

        except Exception as e:
            logger.error(f"❌ Ошибка обновления базы пользователей {profile_name}: {e}")
            return False

    def update_chats_database(self, profile_name: str, chats_list: List[str]) -> bool:
        """Обновляет базу чатов"""
        try:
            if profile_name not in self.profiles:
                logger.error(f"❌ Профиль не найден: {profile_name}")
                return False

            profile_data = self.profiles[profile_name]
            profile_folder = Path(profile_data['folder_path'])

            # Сохраняем в файл
            self._save_chats_database(profile_folder, chats_list)

            # Обновляем в памяти
            profile_data['chats_list'] = chats_list

            logger.info(f"💬 База чатов обновлена для {profile_name}: {len(chats_list)} чатов")
            return True

        except Exception as e:
            logger.error(f"❌ Ошибка обновления базы чатов {profile_name}: {e}")
            return False

    def update_profile_config(self, profile_name: str, config: Dict) -> bool:
        """Обновляет конфигурацию профиля"""
        try:
            if profile_name not in self.profiles:
                logger.error(f"❌ Профиль не найден: {profile_name}")
                return False

            profile_data = self.profiles[profile_name]
            profile_folder = Path(profile_data['folder_path'])

            # Сохраняем в файл
            self._save_config(profile_folder, config)

            # Обновляем в памяти
            profile_data['config'] = config

            logger.info(f"⚙️ Конфигурация обновлена для {profile_name}")
            return True

        except Exception as e:
            logger.error(f"❌ Ошибка обновления конфигурации {profile_name}: {e}")
            return False

    def set_profile_running(self, profile_name: str, is_running: bool):
        """Устанавливает статус запуска профиля"""
        if profile_name in self.profiles:
            self.profiles[profile_name]['is_running'] = is_running
            status = "запущен" if is_running else "остановлен"
            logger.debug(f"📨 Профиль {profile_name} {status}")

    def get_profile_stats(self) -> Dict[str, int]:
        """Получает статистику по профилям"""
        total = len(self.profiles)
        active = sum(1 for p in self.profiles.values() if p.get('is_running', False))

        total_users = sum(len(p.get('users_list', [])) for p in self.profiles.values())
        total_chats = sum(len(p.get('chats_list', [])) for p in self.profiles.values())

        return {
            'total_profiles': total,
            'active_profiles': active,
            'inactive_profiles': total - active,
            'total_users': total_users,
            'total_chats': total_chats
        }

    # ═══════════════════════════════════════════════════════════════════
    # 🔧 ПРИВАТНЫЕ МЕТОДЫ
    # ═══════════════════════════════════════════════════════════════════

    def _create_profile_structure(self, profile_folder: Path):
        """Создает структуру папок профиля"""
        # Основная папка профиля
        profile_folder.mkdir(parents=True, exist_ok=True)

        # Папка для отчетов
        reports_folder = profile_folder / "Отчеты"
        reports_folder.mkdir(exist_ok=True)

        logger.debug(f"📁 Создана структура для профиля: {profile_folder.name}")

    def _create_default_config(self, profile_name: str, initial_settings: Dict = None) -> Dict:
        """Создает конфигурацию по умолчанию"""
        default_config = {
            # Основная информация
            "profile_name": profile_name,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "version": "1.0",

            # Тип инвайта
            "invite_type": "classic",  # classic или admin

            # Настройки работы
            "threads_per_chat": 2,
            "success_per_chat": 0,  # 0 = без ограничений
            "success_per_account": 0,
            "delay_after_start": 0,
            "delay_between": 0,

            # Безопасность аккаунта
            "acc_spam_limit": 3,
            "acc_writeoff_limit": 2,
            "acc_block_invite_limit": 5,

            # Безопасность чата
            "chat_spam_accounts": 3,
            "chat_writeoff_accounts": 2,
            "chat_unknown_error_accounts": 1,
            "chat_freeze_accounts": 1
        }

        # Применяем переданные настройки
        if initial_settings:
            default_config.update(initial_settings)

        return default_config

    def _save_config(self, profile_folder: Path, config: Dict):
        """Сохраняет конфигурацию"""
        config_file = profile_folder / "config.json"
        config["updated_at"] = datetime.now().isoformat()

        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

    def _load_config(self, profile_folder: Path) -> Optional[Dict]:
        """Загружает конфигурацию"""
        config_file = profile_folder / "config.json"

        if not config_file.exists():
            return None

        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки конфигурации {config_file}: {e}")
            return None

    def _create_empty_databases(self, profile_folder: Path):
        """Создает пустые файлы баз данных"""
        users_file = profile_folder / "База юзеров.txt"
        chats_file = profile_folder / "База чатов.txt"

        users_file.write_text("", encoding='utf-8')
        chats_file.write_text("", encoding='utf-8')

    def _save_users_database(self, profile_folder: Path, users_list: List[str]):
        """Сохраняет базу пользователей"""
        users_file = profile_folder / "База юзеров.txt"

        # Очищаем пользователей
        clean_users = []
        for user in users_list:
            user = user.strip()
            if user:
                if user.startswith('@'):
                    user = user[1:]
                if user:
                    clean_users.append(user)

        users_file.write_text('\n'.join(clean_users), encoding='utf-8')

    def _load_users_database(self, profile_folder: Path) -> List[str]:
        """Загружает базу пользователей"""
        users_file = profile_folder / "База юзеров.txt"

        if not users_file.exists():
            return []

        try:
            content = users_file.read_text(encoding='utf-8')
            return [line.strip() for line in content.split('\n') if line.strip()]
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки базы пользователей: {e}")
            return []

    def _save_chats_database(self, profile_folder: Path, chats_list: List[str]):
        """Сохраняет базу чатов"""
        chats_file = profile_folder / "База чатов.txt"

        clean_chats = [chat.strip() for chat in chats_list if chat.strip()]
        chats_file.write_text('\n'.join(clean_chats), encoding='utf-8')

    def _load_chats_database(self, profile_folder: Path) -> List[str]:
        """Загружает базу чатов"""
        chats_file = profile_folder / "База чатов.txt"

        if not chats_file.exists():
            return []

        try:
            content = chats_file.read_text(encoding='utf-8')
            return [line.strip() for line in content.split('\n') if line.strip()]
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки базы чатов: {e}")
            return []

    def _load_profile(self, profile_folder: Path) -> Optional[Dict]:
        """Загружает профиль из папки"""
        try:
            profile_name = profile_folder.name

            # Загружаем конфигурацию
            config = self._load_config(profile_folder)
            if not config:
                logger.warning(f"⚠️ Не удалось загрузить конфигурацию: {profile_name}")
                return None

            # Загружаем базы данных
            users_list = self._load_users_database(profile_folder)
            chats_list = self._load_chats_database(profile_folder)

            return {
                'name': profile_name,
                'folder_path': str(profile_folder),
                'config': config,
                'users_list': users_list,
                'chats_list': chats_list,
                'is_running': False
            }

        except Exception as e:
            logger.error(f"❌ Ошибка загрузки профиля {profile_folder.name}: {e}")
            return None

    def _is_valid_profile(self, profile_folder: Path) -> bool:
        """Проверяет является ли папка валидным профилем"""
        required_files = ["config.json", "База юзеров.txt", "База чатов.txt"]

        for file_name in required_files:
            if not (profile_folder / file_name).exists():
                return False

        return True

    def _sanitize_folder_name(self, name: str) -> str:
        """Очищает название папки"""
        import re

        # Убираем недопустимые символы
        clean_name = re.sub(r'[<>:"/\\|?*]', '', name)
        clean_name = clean_name.strip('. ')

        # Ограничиваем длину
        if len(clean_name) > 100:
            clean_name = clean_name[:100]

        return clean_name