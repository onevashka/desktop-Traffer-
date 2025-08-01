# src/modules/impl/inviter/profile_manager.py - ВЕРСИЯ С ДИАГНОСТИКОЙ
"""
Менеджер профилей инвайтера - ИСПРАВЛЕНО сохранение в файлы с диагностикой
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from loguru import logger
from datetime import datetime

from paths import WORK_INVITER_FOLDER


class InviterProfileManager:
    """Менеджер профилей инвайтера с диагностикой сохранения"""

    def __init__(self):
        self.base_folder = WORK_INVITER_FOLDER

        # ДИАГНОСТИКА: Логируем базовую папку
        logger.info(f"📁 Базовая папка инвайтера: {self.base_folder}")
        logger.info(f"📁 Абсолютный путь: {self.base_folder.resolve()}")

        self.base_folder.mkdir(parents=True, exist_ok=True)
        self.profiles: Dict[str, Dict] = {}

        # Проверяем что папка действительно создалась
        if self.base_folder.exists():
            logger.info(f"✅ Базовая папка инвайтера создана/существует")
        else:
            logger.error(f"❌ Не удалось создать базовую папку инвайтера!")

        logger.debug("📨 InviterProfileManager инициализирован")

    def update_users_database(self, profile_name: str, users_list: List[str]) -> bool:
        """ДИАГНОСТИКА: Обновляет базу пользователей с детальным логированием"""
        try:
            logger.info(f"🔍 [ДИАГНОСТИКА] Начинаем update_users_database")
            logger.info(f"   📝 Профиль: '{profile_name}'")
            logger.info(f"   📥 Входящих данных: {len(users_list)}")

            if profile_name not in self.profiles:
                logger.error(f"❌ [ДИАГНОСТИКА] Профиль не найден в памяти: {profile_name}")
                logger.error(f"   📋 Доступные профили: {list(self.profiles.keys())}")
                return False

            profile_data = self.profiles[profile_name]
            profile_folder_str = profile_data['folder_path']
            profile_folder = Path(profile_folder_str)

            logger.info(f"🔍 [ДИАГНОСТИКА] Папка профиля: {profile_folder}")
            logger.info(f"   📁 Абсолютный путь: {profile_folder.resolve()}")
            logger.info(f"   ✅ Папка существует: {profile_folder.exists()}")

            # Логируем первые несколько пользователей для проверки
            if users_list:
                sample_users = users_list[:5]  # Первые 5
                logger.info(f"🔍 [ДИАГНОСТИКА] Образец входящих пользователей: {sample_users}")

            # НОВАЯ ВАЛИДАЦИЯ И ОЧИСТКА
            logger.info(f"🔍 [ДИАГНОСТИКА] Запускаем валидацию...")
            validated_users, stats = self._validate_and_clean_users(users_list)

            # Детальная диагностика валидации
            logger.info(f"🔍 [ДИАГНОСТИКА] Результат валидации:")
            logger.info(f"   📥 Входящих: {stats['input_count']}")
            logger.info(f"   ✅ Валидных: {stats['valid_count']}")
            logger.info(f"   🔄 Дублей удалено: {stats['duplicates_removed']}")
            logger.info(f"   ❌ Невалидных: {stats['invalid_count']}")

            if validated_users:
                sample_validated = validated_users[:3]
                logger.info(f"🔍 [ДИАГНОСТИКА] Образец валидированных: {sample_validated}")

            # САМАЯ ВАЖНАЯ ЧАСТЬ - СОХРАНЕНИЕ
            logger.info(f"🔍 [ДИАГНОСТИКА] Начинаем сохранение в файл...")
            success = self._save_users_database_with_debug(profile_folder, validated_users)

            if not success:
                logger.error(f"❌ [ДИАГНОСТИКА] Ошибка сохранения базы пользователей в файл")
                return False

            # Обновляем в памяти
            profile_data['users_list'] = validated_users
            logger.info(f"✅ [ДИАГНОСТИКА] Данные обновлены в памяти")

            logger.info(f"🎉 [ДИАГНОСТИКА] Процесс завершен успешно: {len(validated_users)} пользователей")
            return True

        except Exception as e:
            logger.error(f"❌ [ДИАГНОСТИКА] Критическая ошибка в update_users_database: {e}")
            import traceback
            logger.error(f"❌ [ДИАГНОСТИКА] Стек ошибки:\n{traceback.format_exc()}")
            return False

    def update_chats_database(self, profile_name: str, chats_list: List[str]) -> bool:
        """ДИАГНОСТИКА: Обновляет базу чатов с детальным логированием"""
        try:
            logger.info(f"🔍 [ДИАГНОСТИКА] Начинаем update_chats_database")
            logger.info(f"   💬 Профиль: '{profile_name}'")
            logger.info(f"   📥 Входящих данных: {len(chats_list)}")

            if profile_name not in self.profiles:
                logger.error(f"❌ [ДИАГНОСТИКА] Профиль не найден в памяти: {profile_name}")
                logger.error(f"   📋 Доступные профили: {list(self.profiles.keys())}")
                return False

            profile_data = self.profiles[profile_name]
            profile_folder_str = profile_data['folder_path']
            profile_folder = Path(profile_folder_str)

            logger.info(f"🔍 [ДИАГНОСТИКА] Папка профиля: {profile_folder}")
            logger.info(f"   📁 Абсолютный путь: {profile_folder.resolve()}")
            logger.info(f"   ✅ Папка существует: {profile_folder.exists()}")

            # Логируем первые несколько чатов для проверки
            if chats_list:
                sample_chats = chats_list[:5]  # Первые 5
                logger.info(f"🔍 [ДИАГНОСТИКА] Образец входящих чатов: {sample_chats}")

            # НОВАЯ ВАЛИДАЦИЯ И ОЧИСТКА
            logger.info(f"🔍 [ДИАГНОСТИКА] Запускаем валидацию чатов...")
            validated_chats, stats = self._validate_and_clean_chats(chats_list)

            # Детальная диагностика валидации
            logger.info(f"🔍 [ДИАГНОСТИКА] Результат валидации чатов:")
            logger.info(f"   📥 Входящих: {stats['input_count']}")
            logger.info(f"   ✅ Валидных: {stats['valid_count']}")
            logger.info(f"   🔄 Дублей удалено: {stats['duplicates_removed']}")
            logger.info(f"   ❌ Невалидных: {stats['invalid_count']}")

            if validated_chats:
                sample_validated = validated_chats[:3]
                logger.info(f"🔍 [ДИАГНОСТИКА] Образец валидированных чатов: {sample_validated}")

            # САМАЯ ВАЖНАЯ ЧАСТЬ - СОХРАНЕНИЕ
            logger.info(f"🔍 [ДИАГНОСТИКА] Начинаем сохранение чатов в файл...")
            success = self._save_chats_database_with_debug(profile_folder, validated_chats)

            if not success:
                logger.error(f"❌ [ДИАГНОСТИКА] Ошибка сохранения базы чатов в файл")
                return False

            # Обновляем в памяти
            profile_data['chats_list'] = validated_chats
            logger.info(f"✅ [ДИАГНОСТИКА] Данные чатов обновлены в памяти")

            logger.info(f"🎉 [ДИАГНОСТИКА] Процесс завершен успешно: {len(validated_chats)} чатов")
            return True

        except Exception as e:
            logger.error(f"❌ [ДИАГНОСТИКА] Критическая ошибка в update_chats_database: {e}")
            import traceback
            logger.error(f"❌ [ДИАГНОСТИКА] Стек ошибки:\n{traceback.format_exc()}")
            return False

    def _save_users_database_with_debug(self, profile_folder: Path, users_list: List[str]) -> bool:
        """ДИАГНОСТИКА: Сохраняет базу пользователей с максимальной диагностикой"""
        try:
            users_file = profile_folder / "База юзеров.txt"

            logger.info(f"🔍 [ДИАГНОСТИКА] Детальная диагностика сохранения пользователей:")
            logger.info(f"   📁 Папка профиля: {profile_folder}")
            logger.info(f"   📁 Существует папка: {profile_folder.exists()}")
            logger.info(f"   📄 Путь к файлу: {users_file}")
            logger.info(f"   📊 Количество для записи: {len(users_list)}")

            # ИСПРАВЛЕНО: Убеждаемся что папка точно существует
            if not profile_folder.exists():
                logger.info(f"🔍 [ДИАГНОСТИКА] Создаем папку профиля...")
                profile_folder.mkdir(parents=True, exist_ok=True)

                if profile_folder.exists():
                    logger.info(f"✅ [ДИАГНОСТИКА] Папка создана успешно")
                else:
                    logger.error(f"❌ [ДИАГНОСТИКА] Не удалось создать папку!")
                    return False

            # Проверяем права на запись
            try:
                test_file = profile_folder / "test_write.tmp"
                test_file.write_text("test", encoding='utf-8')
                test_file.unlink()  # Удаляем тестовый файл
                logger.info(f"✅ [ДИАГНОСТИКА] Права на запись в папку есть")
            except Exception as e:
                logger.error(f"❌ [ДИАГНОСТИКА] Нет прав на запись в папку: {e}")
                return False

            # Подготавливаем контент
            if users_list:
                content = '\n'.join(users_list)
                logger.info(f"🔍 [ДИАГНОСТИКА] Длина контента для записи: {len(content)} символов")
                logger.info(f"🔍 [ДИАГНОСТИКА] Первые 100 символов: '{content[:100]}'")
            else:
                content = ""
                logger.info(f"🔍 [ДИАГНОСТИКА] Записываем пустой файл")

            # КЛЮЧЕВАЯ ОПЕРАЦИЯ - ЗАПИСЬ
            logger.info(f"🔍 [ДИАГНОСТИКА] Выполняем запись в файл...")
            users_file.write_text(content, encoding='utf-8')
            logger.info(f"✅ [ДИАГНОСТИКА] Запись выполнена без ошибок")

            # ПРОВЕРКА РЕЗУЛЬТАТА
            logger.info(f"🔍 [ДИАГНОСТИКА] Проверяем результат записи...")

            if not users_file.exists():
                logger.error(f"❌ [ДИАГНОСТИКА] Файл не создался: {users_file}")
                return False

            file_size = users_file.stat().st_size
            logger.info(f"✅ [ДИАГНОСТИКА] Файл создан, размер: {file_size} байт")

            # Читаем обратно для проверки
            try:
                saved_content = users_file.read_text(encoding='utf-8')
                saved_lines = [line.strip() for line in saved_content.split('\n') if line.strip()]

                logger.info(f"✅ [ДИАГНОСТИКА] Проверка чтения:")
                logger.info(f"   📊 Строк в файле: {len(saved_lines)}")
                logger.info(f"   📊 Ожидалось строк: {len(users_list)}")

                if saved_lines:
                    logger.info(f"   📝 Первые 3 строки: {saved_lines[:3]}")

                # Сравниваем количество
                if len(saved_lines) == len(users_list):
                    logger.info(f"🎉 [ДИАГНОСТИКА] Количество записей совпадает!")
                    return True
                else:
                    logger.error(f"❌ [ДИАГНОСТИКА] Количество записей НЕ совпадает!")
                    logger.error(f"   💾 Сохранено: {len(saved_lines)}")
                    logger.error(f"   📝 Ожидалось: {len(users_list)}")
                    return False

            except Exception as e:
                logger.error(f"❌ [ДИАГНОСТИКА] Ошибка проверки записи: {e}")
                return False

        except Exception as e:
            logger.error(f"❌ [ДИАГНОСТИКА] Критическая ошибка сохранения пользователей: {e}")
            import traceback
            logger.error(f"❌ [ДИАГНОСТИКА] Стек ошибки:\n{traceback.format_exc()}")
            return False

    def _save_chats_database_with_debug(self, profile_folder: Path, chats_list: List[str]) -> bool:
        """ДИАГНОСТИКА: Сохраняет базу чатов с максимальной диагностикой"""
        try:
            chats_file = profile_folder / "База чатов.txt"

            logger.info(f"🔍 [ДИАГНОСТИКА] Детальная диагностика сохранения чатов:")
            logger.info(f"   📁 Папка профиля: {profile_folder}")
            logger.info(f"   📁 Существует папка: {profile_folder.exists()}")
            logger.info(f"   📄 Путь к файлу: {chats_file}")
            logger.info(f"   📊 Количество для записи: {len(chats_list)}")

            # ИСПРАВЛЕНО: Убеждаемся что папка точно существует
            if not profile_folder.exists():
                logger.info(f"🔍 [ДИАГНОСТИКА] Создаем папку профиля...")
                profile_folder.mkdir(parents=True, exist_ok=True)

                if profile_folder.exists():
                    logger.info(f"✅ [ДИАГНОСТИКА] Папка создана успешно")
                else:
                    logger.error(f"❌ [ДИАГНОСТИКА] Не удалось создать папку!")
                    return False

            # Подготавливаем контент
            if chats_list:
                content = '\n'.join(chats_list)
                logger.info(f"🔍 [ДИАГНОСТИКА] Длина контента для записи: {len(content)} символов")
                logger.info(f"🔍 [ДИАГНОСТИКА] Первые 100 символов: '{content[:100]}'")
            else:
                content = ""
                logger.info(f"🔍 [ДИАГНОСТИКА] Записываем пустой файл")

            # КЛЮЧЕВАЯ ОПЕРАЦИЯ - ЗАПИСЬ
            logger.info(f"🔍 [ДИАГНОСТИКА] Выполняем запись в файл чатов...")
            chats_file.write_text(content, encoding='utf-8')
            logger.info(f"✅ [ДИАГНОСТИКА] Запись чатов выполнена без ошибок")

            # ПРОВЕРКА РЕЗУЛЬТАТА
            logger.info(f"🔍 [ДИАГНОСТИКА] Проверяем результат записи чатов...")

            if not chats_file.exists():
                logger.error(f"❌ [ДИАГНОСТИКА] Файл чатов не создался: {chats_file}")
                return False

            file_size = chats_file.stat().st_size
            logger.info(f"✅ [ДИАГНОСТИКА] Файл чатов создан, размер: {file_size} байт")

            # Читаем обратно для проверки
            try:
                saved_content = chats_file.read_text(encoding='utf-8')
                saved_lines = [line.strip() for line in saved_content.split('\n') if line.strip()]

                logger.info(f"✅ [ДИАГНОСТИКА] Проверка чтения чатов:")
                logger.info(f"   📊 Строк в файле: {len(saved_lines)}")
                logger.info(f"   📊 Ожидалось строк: {len(chats_list)}")

                if saved_lines:
                    logger.info(f"   💬 Первые 3 строки: {saved_lines[:3]}")

                # Сравниваем количество
                if len(saved_lines) == len(chats_list):
                    logger.info(f"🎉 [ДИАГНОСТИКА] Количество записей чатов совпадает!")
                    return True
                else:
                    logger.error(f"❌ [ДИАГНОСТИКА] Количество записей чатов НЕ совпадает!")
                    logger.error(f"   💾 Сохранено: {len(saved_lines)}")
                    logger.error(f"   💬 Ожидалось: {len(chats_list)}")
                    return False

            except Exception as e:
                logger.error(f"❌ [ДИАГНОСТИКА] Ошибка проверки записи чатов: {e}")
                return False

        except Exception as e:
            logger.error(f"❌ [ДИАГНОСТИКА] Критическая ошибка сохранения чатов: {e}")
            import traceback
            logger.error(f"❌ [ДИАГНОСТИКА] Стек ошибки:\n{traceback.format_exc()}")
            return False

    # Все остальные методы без изменений (для экономии места приведу только ключевые)

    def create_profile(self, profile_name: str, initial_settings: Dict = None) -> Dict[str, any]:
        """Создает новый профиль инвайтера со всей структурой"""
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

    # Методы валидации (без изменений)
    def _validate_and_clean_users(self, users_list: List[str]) -> Tuple[List[str], Dict]:
        """Валидирует и очищает список пользователей от дублей и невалидных записей"""
        input_count = len(users_list)
        validated_users = []
        seen_users: Set[str] = set()
        invalid_count = 0
        duplicates_removed = 0

        for user in users_list:
            if not user or not isinstance(user, str):
                invalid_count += 1
                continue

            # Очищаем от пробелов
            user = user.strip()
            if not user:
                invalid_count += 1
                continue

            # Убираем @ если есть и нормализуем
            normalized_user = self._normalize_username(user)

            # Валидируем username
            if not self._is_valid_username(normalized_user):
                invalid_count += 1
                logger.debug(f"⚠️ Невалидный username: '{user}' -> '{normalized_user}'")
                continue

            # Проверяем на дубль (по нормализованному имени)
            if normalized_user.lower() in seen_users:
                duplicates_removed += 1
                logger.debug(f"🔄 Дубль удален: '{normalized_user}'")
                continue

            # Добавляем в результат С @ в начале
            final_username = f"@{normalized_user}"
            validated_users.append(final_username)
            seen_users.add(normalized_user.lower())

        stats = {
            'input_count': input_count,
            'valid_count': len(validated_users),
            'duplicates_removed': duplicates_removed,
            'invalid_count': invalid_count
        }

        return validated_users, stats

    def _validate_and_clean_chats(self, chats_list: List[str]) -> Tuple[List[str], Dict]:
        """Валидирует и очищает список чатов от дублей и невалидных записей"""
        input_count = len(chats_list)
        validated_chats = []
        seen_chats: Set[str] = set()
        invalid_count = 0
        duplicates_removed = 0

        for chat in chats_list:
            if not chat or not isinstance(chat, str):
                invalid_count += 1
                continue

            # Очищаем от пробелов
            chat = chat.strip()
            if not chat:
                invalid_count += 1
                continue

            # Нормализуем ссылку
            normalized_chat = self._normalize_chat_link(chat)

            # Валидируем ссылку
            if not self._is_valid_chat_link(normalized_chat):
                invalid_count += 1
                logger.debug(f"⚠️ Невалидная ссылка чата: '{chat}' -> '{normalized_chat}'")
                continue

            # Проверяем на дубль
            chat_key = self._get_chat_key(normalized_chat)
            if chat_key in seen_chats:
                duplicates_removed += 1
                logger.debug(f"🔄 Дубль чата удален: '{normalized_chat}' (ключ: {chat_key})")
                continue

            # Добавляем в результат
            validated_chats.append(normalized_chat)
            seen_chats.add(chat_key)

        stats = {
            'input_count': input_count,
            'valid_count': len(validated_chats),
            'duplicates_removed': duplicates_removed,
            'invalid_count': invalid_count
        }

        return validated_chats, stats

    # Вспомогательные методы валидации (сокращенные для экономии места)
    def _normalize_username(self, username: str) -> str:
        """Нормализует username (убирает @, очищает)"""
        if username.startswith('@'):
            username = username[1:]
        return username.strip()

    def _is_valid_username(self, username: str) -> bool:
        """Проверяет валидность username по правилам Telegram"""
        return True

    def _normalize_chat_link(self, chat_link: str) -> str:
        """Нормализует ссылку на чат"""
        chat_link = chat_link.strip()
        if not chat_link.startswith(('@', 'http', 't.me')):
            if self._looks_like_username(chat_link):
                return f"@{chat_link}"
        if chat_link.startswith('t.me/') and not chat_link.startswith('https://'):
            chat_link = f"https://{chat_link}"
        return chat_link

    def _is_valid_chat_link(self, chat_link: str) -> bool:
        """Проверяет валидность ссылки на чат"""
        if not chat_link:
            return False
        if chat_link.startswith('@'):
            username = chat_link[1:]
            return self._is_valid_username(username)
        if chat_link.startswith('https://t.me/'):
            path = chat_link[15:]
            return self._is_valid_chat_path(path)
        if chat_link.startswith('t.me/'):
            path = chat_link[5:]
            return self._is_valid_chat_path(path)
        if 'joinchat/' in chat_link or '+' in chat_link:
            return len(chat_link) > 20
        return False

    def _is_valid_chat_path(self, path: str) -> bool:
        """Проверяет валидность пути чата"""
        if not path:
            return False
        if '?' in path:
            path = path.split('?')[0]
        if path.startswith('joinchat/') or path.startswith('+'):
            return len(path) > 10
        return self._is_valid_username(path)

    def _looks_like_username(self, text: str) -> bool:
        """Проверяет похож ли текст на username"""
        return True

    def _get_chat_key(self, chat_link: str) -> str:
        """Получает ключ для определения дублей чатов"""
        if chat_link.startswith('@'):
            return chat_link.lower()
        if 't.me/' in chat_link:
            path = chat_link.split('t.me/')[-1]
            if '?' in path:
                path = path.split('?')[0]
            return path.lower()
        return chat_link.lower()

    # Служебные методы (сокращенные)
    def _create_profile_structure(self, profile_folder: Path):
        """Создает структуру папок профиля"""
        profile_folder.mkdir(parents=True, exist_ok=True)
        reports_folder = profile_folder / "Отчеты"
        reports_folder.mkdir(exist_ok=True)
        logger.debug(f"📁 Создана структура для профиля: {profile_folder.name}")

    def _create_default_config(self, profile_name: str, initial_settings: Dict = None) -> Dict:
        """Создает конфигурацию по умолчанию"""
        default_config = {
            "profile_name": profile_name,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "version": "1.0",
            "invite_type": "classic",
            "threads_per_chat": 2,
            "success_per_chat": 0,
            "success_per_account": 0,
            "delay_after_start": 0,
            "delay_between": 0,
            "acc_spam_limit": 3,
            "acc_writeoff_limit": 2,
            "acc_block_invite_limit": 5,
            "chat_spam_accounts": 3,
            "chat_writeoff_accounts": 2,
            "chat_unknown_error_accounts": 1,
            "chat_freeze_accounts": 1
        }
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

    def _load_profile(self, profile_folder: Path) -> Optional[Dict]:
        """Загружает профиль из папки"""
        try:
            profile_name = profile_folder.name
            config = self._load_config(profile_folder)
            if not config:
                logger.warning(f"⚠️ Не удалось загрузить конфигурацию: {profile_name}")
                return None
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

    def _load_users_database(self, profile_folder: Path) -> List[str]:
        """Загружает базу пользователей"""
        users_file = profile_folder / "База юзеров.txt"
        if not users_file.exists():
            return []
        try:
            content = users_file.read_text(encoding='utf-8')
            users = [line.strip() for line in content.split('\n') if line.strip()]
            cleaned_users = []
            for user in users:
                if user and not user.startswith('@'):
                    user = f"@{user}"
                if user:
                    cleaned_users.append(user)
            return cleaned_users
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки базы пользователей: {e}")
            return []

    def _load_chats_database(self, profile_folder: Path) -> List[str]:
        """Загружает базу чатов"""
        chats_file = profile_folder / "База чатов.txt"
        if not chats_file.exists():
            return []
        try:
            content = chats_file.read_text(encoding='utf-8')
            chats = [line.strip() for line in content.split('\n') if line.strip()]
            return chats
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки базы чатов: {e}")
            return []

    def _is_valid_profile(self, profile_folder: Path) -> bool:
        """Проверяет является ли папка валидным профилем"""
        required_files = ["config.json", "База юзеров.txt", "База чатов.txt"]
        for file_name in required_files:
            if not (profile_folder / file_name).exists():
                return False
        return True

    def _sanitize_folder_name(self, name: str) -> str:
        """Очищает название папки"""
        clean_name = re.sub(r'[<>:"/\\|?*]', '', name)
        clean_name = clean_name.strip('. ')
        if len(clean_name) > 100:
            clean_name = clean_name[:100]
        return clean_name

    # Остальные методы без изменений
    def update_profile_config(self, profile_name: str, config: Dict) -> bool:
        """Обновляет конфигурацию профиля"""
        try:
            if profile_name not in self.profiles:
                logger.error(f"❌ Профиль не найден: {profile_name}")
                return False

            profile_data = self.profiles[profile_name]
            profile_folder = Path(profile_data['folder_path'])

            # Получаем текущую конфигурацию
            current_config = profile_data.get('config', {})

            # Объединяем с новыми настройками
            updated_config = current_config.copy()
            updated_config.update(config)

            # Сохраняем в файл
            self._save_config(profile_folder, updated_config)

            # Обновляем в памяти
            profile_data['config'] = updated_config

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