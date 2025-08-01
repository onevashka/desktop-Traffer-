# src/modules/impl/inviter/inviter_manager.py - ИСПРАВЛЕННАЯ ВЕРСИЯ
"""
Главный менеджер модуля инвайтера - координирует все операции инвайтинга
ОБНОВЛЕННАЯ ВАЛИДАЦИЯ ЧЕРЕЗ PROFILE_MANAGER
"""

from typing import Dict, List, Optional, Tuple
from loguru import logger

from .profile_manager import InviterProfileManager


class InviterModuleManager:
    """
    Главный менеджер модуля инвайтера
    Координирует профили, процессы инвайтинга и статистику
    """

    def __init__(self):
        # Менеджер профилей
        self.profile_manager = InviterProfileManager()

        # Активные процессы инвайтинга
        self.active_processes: Dict[str, any] = {}

        # Статистика
        self._stats_cache = {}

        logger.info("📨 InviterModuleManager инициализирован")

    async def initialize(self):
        """Инициализирует модуль при старте приложения"""
        try:
            logger.info("📨 Инициализация модуля инвайтера...")

            # Загружаем все профили
            await self.load_profiles()

            logger.info("✅ Модуль инвайтера готов!")

        except Exception as e:
            logger.error(f"❌ Ошибка инициализации модуля инвайтера: {e}")

    async def load_profiles(self):
        """Загружает все профили"""
        try:
            profiles = self.profile_manager.load_all_profiles()
            logger.info(f"📨 Загружено профилей: {len(profiles)}")
            self._update_stats_cache()
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки профилей: {e}")

    # ═══════════════════════════════════════════════════════════════════
    # 🎯 УПРАВЛЕНИЕ ПРОФИЛЯМИ
    # ═══════════════════════════════════════════════════════════════════

    def create_profile(self, profile_name: str, initial_settings: Dict = None) -> Dict[str, any]:
        """Создает новый профиль"""
        try:
            result = self.profile_manager.create_profile(profile_name, initial_settings)

            if result['success']:
                self._update_stats_cache()
                logger.info(f"📨 Профиль создан через модуль: {profile_name}")

            return result

        except Exception as e:
            logger.error(f"❌ Ошибка создания профиля в модуле {profile_name}: {e}")
            return {'success': False, 'message': f'Критическая ошибка: {str(e)}'}

    def delete_profile(self, profile_name: str) -> Dict[str, any]:
        """Удаляет профиль"""
        try:
            # Останавливаем процесс если запущен
            if profile_name in self.active_processes:
                self.stop_profile(profile_name)

            result = self.profile_manager.delete_profile(profile_name)

            if result['success']:
                self._update_stats_cache()
                logger.info(f"🗑️ Профиль удален через модуль: {profile_name}")

            return result

        except Exception as e:
            logger.error(f"❌ Ошибка удаления профиля в модуле {profile_name}: {e}")
            return {'success': False, 'message': f'Критическая ошибка: {str(e)}'}

    def get_all_profiles_for_gui(self) -> List[Dict]:
        """Получает все профили для GUI"""
        try:
            profiles = self.profile_manager.get_all_profiles()

            # Дополняем данными о процессах
            for profile in profiles:
                profile_name = profile['name']
                profile['is_running'] = profile_name in self.active_processes

                # Добавляем статистику процесса если есть
                if profile_name in self.active_processes:
                    process = self.active_processes[profile_name]

                    # Базовая статистика процесса
                    profile['process_stats'] = {
                        'is_running': process.is_alive() if hasattr(process, 'is_alive') else True,
                        'profile_name': profile_name,
                        'started_at': process.started_at if hasattr(process, 'started_at') else None
                    }

            return profiles

        except Exception as e:
            logger.error(f"❌ Ошибка получения профилей для GUI: {e}")
            return []

    def update_profile_users(self, profile_name: str, users_list: List[str]) -> bool:
        """
        Обновляет базу пользователей (ИСПОЛЬЗУЕТ ВАЛИДАЦИЮ ИЗ PROFILE_MANAGER)
        """
        try:
            # Теперь вся валидация происходит в profile_manager
            success = self.profile_manager.update_users_database(profile_name, users_list)

            if success:
                self._update_stats_cache()
                logger.info(f"📝 База пользователей обновлена через модуль: {profile_name}")

            return success

        except Exception as e:
            logger.error(f"❌ Ошибка обновления пользователей в модуле {profile_name}: {e}")
            return False

    def update_profile_chats(self, profile_name: str, chats_list: List[str]) -> bool:
        """
        Обновляет базу чатов (ИСПОЛЬЗУЕТ ВАЛИДАЦИЮ ИЗ PROFILE_MANAGER)
        """
        try:
            # Теперь вся валидация происходит в profile_manager
            success = self.profile_manager.update_chats_database(profile_name, chats_list)

            if success:
                self._update_stats_cache()
                logger.info(f"💬 База чатов обновлена через модуль: {profile_name}")

            return success

        except Exception as e:
            logger.error(f"❌ Ошибка обновления чатов в модуле {profile_name}: {e}")
            return False

    def update_profile_config(self, profile_name: str, config: Dict) -> bool:
        """Обновляет конфигурацию профиля"""
        try:
            # Валидируем конфигурацию
            validated_config = self._validate_config(config)

            success = self.profile_manager.update_profile_config(profile_name, validated_config)

            if success:
                logger.info(f"⚙️ Конфигурация обновлена через модуль: {profile_name}")

            return success

        except Exception as e:
            logger.error(f"❌ Ошибка обновления конфигурации в модуле {profile_name}: {e}")
            return False

    # ═══════════════════════════════════════════════════════════════════
    # 🚀 УПРАВЛЕНИЕ ПРОЦЕССАМИ ИНВАЙТИНГА
    # ═══════════════════════════════════════════════════════════════════

    def start_profile(self, profile_name: str) -> bool:
        """Запускает процесс инвайтинга для профиля"""
        try:
            profile = self.profile_manager.get_profile(profile_name)
            if not profile:
                logger.error(f"❌ Профиль не найден: {profile_name}")
                return False

            if profile_name in self.active_processes:
                logger.warning(f"⚠️ Профиль уже запущен: {profile_name}")
                return True

            # Валидация перед запуском
            validation = self._validate_profile_for_start(profile)
            if not validation['valid']:
                logger.error(f"❌ Профиль не готов к запуску: {validation['message']}")
                return False

            # Получаем AccountManager
            from src.accounts.manager import _account_manager
            if not _account_manager:
                logger.error("❌ AccountManager не инициализирован")
                return False

            # Создаем процесс инвайтинга в зависимости от типа
            invite_type = profile.get('config', {}).get('invite_type', 'classic')

            if invite_type == 'Классический':
                from .classic_inviter import ClassicInviterProcess
                inviter_process = ClassicInviterProcess(
                    profile_name=profile_name,
                    profile_data=profile,
                    account_manager=_account_manager
                )
            else:
                logger.error(f"❌ Неизвестный тип инвайта: {invite_type}")
                return False

            # Запускаем поток
            inviter_process.start()

            # Сохраняем процесс
            self.active_processes[profile_name] = inviter_process

            # Обновляем статус в профиле
            self.profile_manager.set_profile_running(profile_name, True)
            self._update_stats_cache()

            logger.info(f"🚀 Профиль запущен: {profile_name}")
            return True

        except Exception as e:
            logger.error(f"❌ Ошибка запуска профиля {profile_name}: {e}")
            return False

    def stop_profile(self, profile_name: str) -> bool:
        """Останавливает процесс инвайтинга для профиля"""
        try:
            if profile_name not in self.active_processes:
                logger.warning(f"⚠️ Профиль не запущен: {profile_name}")
                return True

            # Получаем процесс
            process = self.active_processes[profile_name]

            # Останавливаем процесс
            if hasattr(process, 'stop'):
                process.stop()

                # Ждем завершения (максимум 10 секунд)
                process.join(timeout=10)

                if process.is_alive():
                    logger.warning(f"⚠️ Процесс {profile_name} не завершился в течение 10 секунд")

            del self.active_processes[profile_name]

            # Обновляем статус в профиле
            self.profile_manager.set_profile_running(profile_name, False)
            self._update_stats_cache()

            logger.info(f"⏸️ Профиль остановлен: {profile_name}")
            return True

        except Exception as e:
            logger.error(f"❌ Ошибка остановки профиля {profile_name}: {e}")
            return False

    def start_all_profiles(self) -> Dict[str, bool]:
        """Запускает все профили"""
        results = {}
        profiles = self.profile_manager.get_all_profiles()

        for profile in profiles:
            profile_name = profile['name']
            results[profile_name] = self.start_profile(profile_name)

        success_count = sum(results.values())
        logger.info(f"🚀 Массовый запуск через модуль: {success_count}/{len(results)} успешно")
        return results

    def stop_all_profiles(self) -> Dict[str, bool]:
        """Останавливает все профили"""
        results = {}

        for profile_name in list(self.active_processes.keys()):
            results[profile_name] = self.stop_profile(profile_name)

        success_count = sum(results.values())
        logger.info(f"⏸️ Массовая остановка через модуль: {success_count}/{len(results)} успешно")
        return results

    # ═══════════════════════════════════════════════════════════════════
    # 📊 СТАТИСТИКА И АНАЛИТИКА
    # ═══════════════════════════════════════════════════════════════════

    def get_inviter_stats(self) -> List[Tuple[str, str, str, str]]:
        """
        Статистика для GUI инвайтера

        Returns:
            List[Tuple[str, str, str, str]]: [(название, значение, цвет, ключ), ...]
        """
        try:
            stats = self.profile_manager.get_profile_stats()

            # Подсчитываем инвайты из активных процессов
            total_success = sum(
                proc.get('stats', {}).get('success', 0)
                for proc in self.active_processes.values()
            )

            total_errors = sum(
                proc.get('stats', {}).get('errors', 0)
                for proc in self.active_processes.values()
            )

            return [
                ("Активных профилей", str(stats['active_profiles']), "#10B981", "active_profiles"),
                ("Всего профилей", str(stats['total_profiles']), "#3B82F6", "total_profiles"),
                ("Успешных инвайтов", str(total_success), "#059669", "success_invites"),
                ("Ошибок", str(total_errors), "#EF4444", "errors"),
                ("Пользователей в базах", str(stats['total_users']), "#8B5CF6", "total_users"),
                ("Чатов в базах", str(stats['total_chats']), "#F59E0B", "total_chats")
            ]

        except Exception as e:
            logger.error(f"❌ Ошибка получения статистики: {e}")
            return [("Ошибка загрузки", "0", "#EF4444", "error")]

    def get_detailed_stats(self) -> Dict:
        """Получает детальную статистику модуля"""
        try:
            profile_stats = self.profile_manager.get_profile_stats()

            # Статистика процессов
            process_stats = {}
            for profile_name, process in self.active_processes.items():
                process_stats[profile_name] = process.get('stats', {})

            return {
                'profiles': profile_stats,
                'processes': process_stats,
                'module_status': 'active' if self.active_processes else 'idle'
            }

        except Exception as e:
            logger.error(f"❌ Ошибка получения детальной статистики: {e}")
            return {}

    def get_profile_status(self, profile_name: str) -> Dict:
        """Получает статус конкретного профиля"""
        try:
            profile = self.profile_manager.get_profile(profile_name)
            if not profile:
                return {'exists': False}

            is_running = profile_name in self.active_processes
            process_info = self.active_processes.get(profile_name, {})

            return {
                'exists': True,
                'is_running': is_running,
                'process_info': process_info,
                'users_count': len(profile.get('users_list', [])),
                'chats_count': len(profile.get('chats_list', [])),
                'config': profile.get('config', {})
            }

        except Exception as e:
            logger.error(f"❌ Ошибка получения статуса профиля {profile_name}: {e}")
            return {'exists': False, 'error': str(e)}

    # ═══════════════════════════════════════════════════════════════════
    # 🔧 СЛУЖЕБНЫЕ МЕТОДЫ (УПРОЩЕННЫЕ, ВАЛИДАЦИЯ ВЫНЕСЕНА В PROFILE_MANAGER)
    # ═══════════════════════════════════════════════════════════════════

    def _validate_config(self, config: Dict) -> Dict:
        """Валидирует конфигурацию профиля"""
        # Устанавливаем безопасные значения по умолчанию
        safe_config = config.copy()

        # Проверяем критические параметры
        if safe_config.get('threads_per_chat', 0) < 1:
            safe_config['threads_per_chat'] = 1
        elif safe_config.get('threads_per_chat', 0) > 10:
            safe_config['threads_per_chat'] = 10

        # Проверяем лимиты
        for limit_key in ['success_per_chat', 'success_per_account']:
            if safe_config.get(limit_key, 0) < 0:
                safe_config[limit_key] = 0

        # Проверяем задержки
        for delay_key in ['delay_after_start', 'delay_between']:
            if safe_config.get(delay_key, 0) < 0:
                safe_config[delay_key] = 0

        return safe_config

    def _validate_profile_for_start(self, profile_data: Dict) -> Dict[str, any]:
        """Валидирует профиль перед запуском"""
        errors = []

        # Проверяем базу пользователей
        users_list = profile_data.get('users_list', [])
        if not users_list:
            errors.append("База пользователей пуста")

        # Проверяем базу чатов
        chats_list = profile_data.get('chats_list', [])
        if not chats_list:
            errors.append("База чатов пуста")

        # Проверяем конфигурацию
        config = profile_data.get('config', {})
        if not config:
            errors.append("Отсутствует конфигурация профиля")

        # Проверяем доступность аккаунтов
        from src.accounts.manager import _account_manager
        if _account_manager:
            active_accounts = [
                acc for acc in _account_manager.traffic_accounts.values()
                if acc.status == "active"
            ]
            if not active_accounts:
                errors.append("Нет активных аккаунтов для инвайтинга")
        else:
            errors.append("AccountManager не инициализирован")

        if errors:
            return {
                'valid': False,
                'message': '; '.join(errors)
            }

        return {'valid': True, 'message': 'Профиль готов к запуску'}

    def _update_stats_cache(self):
        """Обновляет кеш статистики"""
        try:
            self._stats_cache = {
                'updated_at': 'now',
                'profiles': self.profile_manager.get_profile_stats(),
                'processes': len(self.active_processes)
            }
        except Exception as e:
            logger.error(f"❌ Ошибка обновления кеша статистики: {e}")

    def refresh_all(self):
        """Полное обновление модуля"""
        try:
            logger.info("🔄 Полное обновление модуля инвайтера...")

            # Останавливаем все процессы
            self.stop_all_profiles()

            # Перезагружаем профили
            self.profile_manager.load_all_profiles()

            # Обновляем кеш
            self._update_stats_cache()

            logger.info("✅ Модуль инвайтера обновлен")

        except Exception as e:
            logger.error(f"❌ Ошибка обновления модуля инвайтера: {e}")


# ═══════════════════════════════════════════════════════════════════
# 🌍 ГЛОБАЛЬНЫЙ ЭКЗЕМПЛЯР ДЛЯ МОДУЛЕЙ (БЕЗ ИЗМЕНЕНИЙ)
# ═══════════════════════════════════════════════════════════════════

_inviter_module_manager: Optional[InviterModuleManager] = None


async def get_inviter_module_manager() -> InviterModuleManager:
    """Получает глобальный экземпляр менеджера модуля инвайтера"""
    global _inviter_module_manager
    if _inviter_module_manager is None:
        _inviter_module_manager = InviterModuleManager()
        await _inviter_module_manager.initialize()
    return _inviter_module_manager


async def init_inviter_module() -> InviterModuleManager:
    """Инициализирует модуль инвайтера при старте приложения"""
    global _inviter_module_manager
    logger.info("📨 Инициализация модуля инвайтера...")
    _inviter_module_manager = await get_inviter_module_manager()
    logger.info("✅ Модуль инвайтера готов!")
    return _inviter_module_manager


# ═══════════════════════════════════════════════════════════════════
# 🎨 ФУНКЦИИ ДЛЯ GUI - обертки для удобства (БЕЗ ИЗМЕНЕНИЙ)
# ═══════════════════════════════════════════════════════════════════

def get_inviter_stats() -> List[Tuple[str, str, str, str]]:
    """Получает статистику для GUI"""
    global _inviter_module_manager
    if _inviter_module_manager:
        return _inviter_module_manager.get_inviter_stats()
    return [("Не загружено", "0", "#EF4444", "error")]


def get_all_profiles_for_gui() -> List[Dict]:
    """Получает все профили для GUI"""
    global _inviter_module_manager
    if _inviter_module_manager:
        return _inviter_module_manager.get_all_profiles_for_gui()
    return []


def create_profile(profile_name: str, initial_settings: Dict = None) -> Dict[str, any]:
    """Создает профиль через GUI"""
    global _inviter_module_manager
    if _inviter_module_manager:
        return _inviter_module_manager.create_profile(profile_name, initial_settings)
    return {'success': False, 'message': 'Модуль не инициализирован'}


def delete_profile(profile_name: str) -> Dict[str, any]:
    """Удаляет профиль через GUI"""
    global _inviter_module_manager
    if _inviter_module_manager:
        return _inviter_module_manager.delete_profile(profile_name)
    return {'success': False, 'message': 'Модуль не инициализирован'}


def start_profile(profile_name: str) -> bool:
    """Запускает профиль через GUI"""
    global _inviter_module_manager
    if _inviter_module_manager:
        return _inviter_module_manager.start_profile(profile_name)
    return False


def stop_profile(profile_name: str) -> bool:
    """Останавливает профиль через GUI"""
    global _inviter_module_manager
    if _inviter_module_manager:
        return _inviter_module_manager.stop_profile(profile_name)
    return False


def update_profile_users(profile_name: str, users_list: List[str]) -> bool:
    """Обновляет базу пользователей через GUI"""
    global _inviter_module_manager
    if _inviter_module_manager:
        return _inviter_module_manager.update_profile_users(profile_name, users_list)
    return False


def update_profile_chats(profile_name: str, chats_list: List[str]) -> bool:
    """Обновляет базу чатов через GUI"""
    global _inviter_module_manager
    if _inviter_module_manager:
        return _inviter_module_manager.update_profile_chats(profile_name, chats_list)
    return False


def update_profile_config(profile_name: str, config: Dict) -> bool:
    """Обновляет конфигурацию профиля через GUI"""
    global _inviter_module_manager
    if _inviter_module_manager:
        return _inviter_module_manager.update_profile_config(profile_name, config)
    return False


def start_all_profiles() -> Dict[str, bool]:
    """Запускает все профили через GUI"""
    global _inviter_module_manager
    if _inviter_module_manager:
        return _inviter_module_manager.start_all_profiles()
    return {}


def stop_all_profiles() -> Dict[str, bool]:
    """Останавливает все профили через GUI"""
    global _inviter_module_manager
    if _inviter_module_manager:
        return _inviter_module_manager.stop_all_profiles()
    return {}


def refresh_inviter_module():
    """Обновляет модуль инвайтера через GUI"""
    global _inviter_module_manager
    if _inviter_module_manager:
        _inviter_module_manager.refresh_all()


def get_profile_progress(profile_name: str) -> Optional[Dict]:
    """Получает прогресс выполнения профиля относительно целей"""
    global _inviter_module_manager
    if _inviter_module_manager and profile_name in _inviter_module_manager.active_processes:
        process = _inviter_module_manager.active_processes[profile_name]

        # Базовые данные прогресса
        progress_data = {
            'profile_name': profile_name,
            'is_running': process.is_alive() if hasattr(process, 'is_alive') else False
        }

        # Получаем данные из процесса если доступны
        if hasattr(process, 'total_processed'):
            progress_data['processed'] = process.total_processed
        else:
            progress_data['processed'] = 0

        if hasattr(process, 'total_success'):
            progress_data['success'] = process.total_success
        else:
            progress_data['success'] = 0

        if hasattr(process, 'total_errors'):
            progress_data['errors'] = process.total_errors
        else:
            progress_data['errors'] = 0

        # ВАЖНО: Рассчитываем цель на основе конфигурации
        if hasattr(process, 'config'):
            config = process.config
            chats_count = process.chat_queue.qsize() if hasattr(process, 'chat_queue') else 0

            # Если есть начальное количество чатов
            if hasattr(process, 'initial_chats_count'):
                chats_count = process.initial_chats_count

            # Рассчитываем общую цель инвайтов
            if config.success_per_chat > 0:
                # Если есть лимит на чат - цель = количество чатов * лимит на чат
                total_goal = chats_count * config.success_per_chat
            elif config.success_per_account > 0:
                # Если есть лимит на аккаунт - цель = количество аккаунтов * лимит на аккаунт
                accounts_count = len(process.account_stats) if hasattr(process, 'account_stats') else 1
                total_goal = accounts_count * config.success_per_account
            else:
                # Если нет лимитов - цель = количество пользователей
                total_goal = len(process.processed_users) + process.user_queue.qsize() if hasattr(process,
                                                                                                  'user_queue') else 100

            progress_data['total_goal'] = total_goal
            progress_data['total_users'] = total_goal  # Для совместимости
        else:
            progress_data['total_goal'] = 100
            progress_data['total_users'] = 100

        # Скорость обработки
        if hasattr(process, 'started_at') and process.started_at:
            from datetime import datetime
            elapsed = (datetime.now() - process.started_at).total_seconds()
            if elapsed > 0:
                speed = int((progress_data['success'] / elapsed) * 60)  # успешных в минуту
                progress_data['speed'] = speed
            else:
                progress_data['speed'] = 0
        else:
            progress_data['speed'] = 0

        # Детальный статус процесса
        if progress_data['is_running']:
            if hasattr(process, 'chat_threads'):
                active_threads = sum(1 for t in process.chat_threads if t.is_alive())
                if active_threads > 0:
                    progress_data['status'] = f"Работает ({active_threads} потоков)"
                else:
                    progress_data['status'] = "Завершение работы..."
            else:
                progress_data['status'] = "Инициализация..."

            # Проверяем достигнута ли цель
            if progress_data['success'] >= progress_data['total_goal'] and progress_data['total_goal'] > 0:
                progress_data['status'] = "✅ Цель достигнута!"
        else:
            progress_data['status'] = "Остановлен"

        # Добавляем информацию об активных аккаунтах
        if hasattr(process, 'account_stats'):
            active_accounts = sum(1 for stats in process.account_stats.values()
                                  if hasattr(stats, 'status') and stats.status == 'working')
            finished_accounts = sum(1 for stats in process.account_stats.values()
                                    if hasattr(stats, 'status') and stats.status == 'finished')
            progress_data['active_accounts'] = active_accounts
            progress_data['finished_accounts'] = finished_accounts

        return progress_data

    return None