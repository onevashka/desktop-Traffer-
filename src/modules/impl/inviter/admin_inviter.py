# src/modules/impl/inviter/admin_inviter.py - ОПТИМИЗИРОВАННАЯ ВЕРСИЯ
"""
ОПТИМИЗИРОВАНО: Админ-инвайтер с системой реального времени
- Убрано избыточное сохранение в конце процесса
- Все записи ведутся в реальном времени
- Оставлен только необходимый функционал
"""
import asyncio
import queue
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from loguru import logger
from pathlib import Path
from dataclasses import dataclass

from .base_inviter import BaseInviterProcess
from .bot_manager import BotManager
from .admin_rights_manager import AdminRightsManager
from .account_mover import AccountMover
from .worker_thread import ChatWorkerThread
from .account_error_counters import AccountErrorManager
from .progress_manager import ProgressManager
from .report_generator import ReportGenerator
from .realtime_logger import RealtimeLogger  # ДОБАВЛЕНО
from .utils import clean_expired_accounts, ensure_main_admin_ready_in_chat
from src.entities.moduls.inviter import *
from .chat_protection import ChatProtectionManager


class AdminInviterProcess(BaseInviterProcess):
    """Главный класс админ-инвайтера с системой реального времени"""

    def __init__(self, profile_name: str, profile_data: Dict, account_manager):
        super().__init__(profile_name, profile_data, account_manager)

        profile_folder = Path(profile_data['folder_path'])
        from .data_loader import InviterDataLoader
        loader = InviterDataLoader(profile_folder)
        self.bot_token = loader._load_bot_token()

        # НОВОЕ: Главные админы для каждого чата
        admins_folder = profile_folder / "Админы"
        self.available_admins = []
        self.chat_admins: Dict[str, ChatAdmin] = {}

        if admins_folder.exists():
            session_files = list(admins_folder.glob("*.session"))
            for session_file in session_files:
                admin_name = session_file.stem
                json_file = admins_folder / f"{admin_name}.json"
                if json_file.exists():
                    self.available_admins.append(admin_name)
                    logger.success(f"[{self.profile_name}] Найден админ: {admin_name}")

        logger.info(f"[{self.profile_name}] Всего доступных админов: {len(self.available_admins)}")

        # Инициализация делегированных менеджеров
        self.account_mover = AccountMover(profile_folder)
        self.error_manager = AccountErrorManager(self)
        self.progress_manager = ProgressManager(self)
        self.report_generator = ReportGenerator(self)

        # НОВОЕ: Система реального времени
        self.realtime_logger = RealtimeLogger(profile_name, profile_folder)

        # Основные менеджеры
        self.bot_manager: Optional[BotManager] = None
        self.admin_rights_manager: Optional[AdminRightsManager] = None

        # Очереди и потоки
        self.admin_command_queue = queue.Queue()
        self.chat_threads = []
        self.ready_chats = set()

        # Статистика
        self.account_stats: Dict[str, AccountStats] = {}
        self.total_success = 0
        self.total_errors = 0
        self.total_processed = 0
        self.frozen_accounts = set()
        self.finished_accounts = set()
        self.blocked_accounts = set()
        self.account_finish_times: Dict[str, datetime] = {}
        self.chat_stats: Dict[str, Dict] = {}

        # Специфичные типы проблем для правильного перемещения
        self.writeoff_accounts = set()
        self.spam_block_accounts = set()
        self.block_invite_accounts = set()
        self.finished_successfully_accounts = set()
        self.processed_accounts = set()

        # Путь к файлу пользователей
        self.users_file_path = profile_folder / "База юзеров.txt"

        self.chat_threads = []
        self.shutdown_in_progress = False

        self.chat_protection_manager = ChatProtectionManager(self)

    # ============================================================================
    # ДЕЛЕГИРОВАННЫЕ МЕТОДЫ - используют специализированные менеджеры
    # ============================================================================

    def _check_account_error_limits(self, account_name: str, error_type: str) -> bool:
        """Делегируем AccountErrorManager"""
        return self.error_manager.check_error_limits(account_name, error_type)

    def _mark_account_as_processed(self, account_name: str, reason: str):
        """Делегируем AccountErrorManager"""
        self.error_manager.mark_account_as_processed(account_name, reason)

    def _update_account_status_in_manager_sync(self, account_name: str, new_status: str):
        """Делегируем AccountErrorManager"""
        self.error_manager.update_account_status_in_manager_sync(account_name, new_status)

    def _save_users_progress_to_file(self):
        """УБРАНО - больше не нужно, все записывается в реальном времени"""
        pass

    def _load_user_statuses(self):
        """Делегируем ProgressManager"""
        self.progress_manager.load_user_statuses()

    def _save_user_statuses(self):
        """УБРАНО - больше не нужно, все записывается в реальном времени"""
        pass

    def _generate_final_report(self):
        """Делегируем ReportGenerator"""
        self.report_generator.generate_final_report()

    # ============================================================================
    # ОСНОВНАЯ ЛОГИКА ПРОЦЕССА (остается в главном классе)
    # ============================================================================

    def get_fresh_accounts(self, module_name: str, count: int) -> List:
        """Получение свежих аккаунтов с проверкой уже обработанных"""
        try:
            accounts = self.account_manager.get_free_accounts(module_name, count)

            if not accounts:
                logger.warning(f"[{self.profile_name}] Менеджер не предоставил аккаунты (запрошено: {count})")
                return []

            fresh_accounts = []
            for account_data in accounts:
                if account_data.name not in self.processed_accounts:
                    fresh_accounts.append(account_data)
                else:
                    try:
                        self.account_manager.release_account(account_data.name, module_name)
                    except Exception as e:
                        logger.error(
                            f"[{self.profile_name}] Ошибка освобождения обработанного аккаунта {account_data.name}: {e}")

            if fresh_accounts:
                pass
            else:
                logger.warning(f"[{self.profile_name}] Все полученные аккаунты уже были обработаны")

            return fresh_accounts

        except Exception as e:
            logger.error(f"[{self.profile_name}] Ошибка получения аккаунтов от менеджера: {e}")
            return []

    def check_accounts_availability(self) -> bool:
        """Проверяет есть ли доступные неиспользованные аккаунты у менеджера"""
        try:
            free_count = self.account_manager.get_free_accounts_count()
            estimated_available = max(0, free_count - len(self.processed_accounts))
            return estimated_available > 0
        except Exception as e:
            logger.error(f"[{self.profile_name}] Ошибка проверки доступности аккаунтов: {e}")
            return False

    def _assign_admins_to_chats(self):
        """Назначает отдельного админа каждому чату"""
        # Получаем все чаты
        chat_links = []
        temp_chats = []
        while not self.chat_queue.empty():
            chat = self.chat_queue.get_nowait()
            chat_links.append(chat)
            temp_chats.append(chat)
        for chat in temp_chats:
            self.chat_queue.put(chat)

        if not chat_links:
            logger.error(f"[{self.profile_name}] Нет чатов для назначения админов")
            return False

        if len(self.available_admins) < len(chat_links):
            logger.error(
                f"[{self.profile_name}] Недостаточно админов: {len(self.available_admins)} админов для {len(chat_links)} чатов")
            return False

        # Назначаем админа каждому чату
        profile_folder = Path(self.profile_data['folder_path'])
        admins_folder = profile_folder / "Админы"

        for i, chat_link in enumerate(chat_links):
            admin_name = self.available_admins[i]
            chat_admin = ChatAdmin(
                name=admin_name,
                session_path=admins_folder / f"{admin_name}.session",
                json_path=admins_folder / f"{admin_name}.json"
            )
            self.chat_admins[chat_link] = chat_admin
            logger.success(f"[{self.profile_name}] Чат {chat_link} -> Админ {admin_name}")

        return True

    def _run_inviting(self):
        """ОПТИМИЗИРОВАННАЯ логика без избыточного сохранения"""
        logger.success(f"[{self.profile_name}] Запуск админ-инвайтинга")

        if not self.bot_token or not self.available_admins:
            logger.error(f"[{self.profile_name}] Не настроен бот или нет админов")
            return

        self._load_user_statuses()

        try:
            asyncio.run(self._async_run_inviting())
        except Exception as e:
            logger.error(f"[{self.profile_name}] Критическая ошибка: {e}")
        finally:
            self.is_running = False
            self.finished_at = datetime.now()

            # ОПТИМИЗИРОВАНО: Показываем итоговую статистику (но не сохраняем файлы - они уже актуальны)
            total_processed = len(self.processed_users)
            successful_invites = sum(1 for user in self.processed_users.values() if user.status == UserStatus.INVITED)
            privacy_restricted = sum(1 for user in self.processed_users.values() if user.status == UserStatus.PRIVACY)
            spam_blocks = sum(1 for user in self.processed_users.values() if user.status == UserStatus.SPAM_BLOCK)
            not_found = sum(1 for user in self.processed_users.values() if user.status == UserStatus.NOT_FOUND)
            already_in = sum(1 for user in self.processed_users.values() if user.status == UserStatus.ALREADY_IN)
            errors = sum(1 for user in self.processed_users.values() if user.status == UserStatus.ERROR)

            success_rate = (successful_invites / total_processed * 100) if total_processed > 0 else 0

            logger.success(f"")
            logger.success(f"🎯 [{self.profile_name}] ФИНАЛЬНАЯ СТАТИСТИКА:")
            logger.success(f"📊 Всего обработано: {total_processed} пользователей")
            logger.success(f"✅ Успешно добавлено: {successful_invites} чел.")
            logger.success(f"🔒 Приватные ограничения: {privacy_restricted} чел.")
            logger.success(f"🚫 Спам-блоки: {spam_blocks} чел.")
            logger.success(f"🔍 Не найдено: {not_found} чел.")
            logger.success(f"👥 Уже в чатах: {already_in} чел.")
            logger.success(f"❌ Прочие ошибки: {errors} чел.")
            logger.success(f"📈 Процент успеха: {success_rate:.1f}%")
            logger.success(f"")

            # Генерируем итоговый отчет в папке Отчеты/
            self._generate_final_report()

            # Завершаем отчет реального времени
            self.realtime_logger.finalize_report(total_processed, successful_invites)

    async def _async_run_inviting(self):
        """Асинхронная логика"""
        try:
            if not await self._init_bot():
                return
            if not await self._setup_bot():
                return
            if not self._assign_admins_to_chats():
                return
            if not await self._setup_chat_admins():
                return
            if not await self._prepare_admins_in_chats():
                return
            await self._main_work_loop()
        except Exception as e:
            logger.error(f"[{self.profile_name}] Ошибка: {e}")
        finally:
            await self._cleanup()

    async def _init_bot(self) -> bool:
        """Инициализация бота"""
        try:
            self.bot_manager = BotManager(bot_token=self.bot_token, proxy_url=None)
            if not await self.bot_manager.connect():
                return False
            self.admin_rights_manager = AdminRightsManager(bot_manager=self.bot_manager)
            return True
        except Exception as e:
            logger.error(f"[{self.profile_name}] Ошибка бота: {e}")
            return False

    async def _setup_bot(self) -> bool:
        """Настройка бота пользователем"""
        chat_links = []
        temp_chats = []
        while not self.chat_queue.empty():
            chat = self.chat_queue.get_nowait()
            chat_links.append(chat)
            temp_chats.append(chat)
        for chat in temp_chats:
            self.chat_queue.put(chat)

        if not chat_links:
            return False

        setup_needed = []
        for chat in chat_links:
            is_admin = await self.bot_manager.check_bot_admin_status(chat)
            if not is_admin:
                setup_needed.append(chat)
                logger.warning(f"[{self.profile_name}] Требует настройки: {chat}")
            else:
                logger.success(f"[{self.profile_name}] Бот готов в чате: {chat}")

        if setup_needed:
            await asyncio.sleep(60)

        return True

    async def _setup_chat_admins(self) -> bool:
        """Создание и подключение админов для каждого чата"""
        try:
            for chat_link, chat_admin in self.chat_admins.items():
                logger.info(f"[{self.profile_name}] Настройка админа {chat_admin.name} для чата {chat_link}")

                if not chat_admin.session_path.exists() or not chat_admin.json_path.exists():
                    logger.error(f"[{self.profile_name}] Файлы админа {chat_admin.name} не найдены")
                    return False

                from src.accounts.impl.account import Account
                chat_admin.account = Account(
                    session_path=chat_admin.session_path,
                    json_path=chat_admin.json_path
                )
                await chat_admin.account.create_client()

                if not await chat_admin.account.connect():
                    logger.error(f"[{self.profile_name}] Не удалось подключить админа {chat_admin.name}")
                    return False

                if not await chat_admin.account.client.is_user_authorized():
                    logger.error(f"[{self.profile_name}] Админ {chat_admin.name} не авторизован")
                    return False

                me = await chat_admin.account.client.get_me()
                logger.success(
                    f"[{self.profile_name}] Админ {chat_admin.name} подключен: {me.first_name} (@{me.username or 'без username'})")

            return True

        except Exception as e:
            logger.error(f"[{self.profile_name}] Ошибка настройки админов: {e}")
            return False

    async def _prepare_admins_in_chats(self) -> bool:
        """Подготовка каждого админа в его чате"""
        for chat_link, chat_admin in self.chat_admins.items():
            logger.info(f"[{self.profile_name}] Подготовка админа {chat_admin.name} в чате {chat_link}")

            success = await ensure_main_admin_ready_in_chat(
                main_admin_account=chat_admin.account,
                admin_rights_manager=self.admin_rights_manager,
                chat_link=chat_link
            )

            if success:
                chat_admin.is_ready = True
                self.ready_chats.add(chat_link)
                logger.success(f"[{self.profile_name}] Админ {chat_admin.name} готов в чате: {chat_link}")
            else:
                logger.error(
                    f"[{self.profile_name}] Не удалось подготовить админа {chat_admin.name} в чате: {chat_link}")

        if not self.ready_chats:
            logger.error(f"[{self.profile_name}] Ни один админ не готов! Прекращаем работу.")
            return False

        logger.success(f"[{self.profile_name}] Готовых чатов: {len(self.ready_chats)} из {len(self.chat_admins)}")
        return True

    async def _main_work_loop(self):
        """ИСПРАВЛЕННЫЙ главный цикл без зацикливания"""
        if self.config.delay_after_start > 0:
            await asyncio.sleep(self.config.delay_after_start)

        await self._start_chats()

        if not self.chat_threads:
            logger.error(f"[{self.profile_name}] Нет запущенных потоков чатов!")
            return

        # ФЛАГ для предотвращения зацикливания
        work_finished = False

        while not self.stop_flag.is_set() and not work_finished:
            try:
                # Обрабатываем команды от воркеров
                try:
                    command = self.admin_command_queue.get_nowait()
                    await self._execute_admin_command(command)
                except queue.Empty:
                    pass

                # Проверяем состояние потоков
                alive_threads = [t for t in self.chat_threads if t.is_alive()]

                if not alive_threads:
                    # Все потоки завершились - логируем ОДИН РАЗ и завершаем
                    logger.info(f"🎯 [{self.profile_name}] Все потоки завершены - работа окончена!")
                    work_finished = True  # КРИТИЧНО: устанавливаем флаг завершения
                    break

                # Дополнительная проверка: если нет пользователей И нет живых потоков
                if self.user_queue.empty() and not alive_threads:
                    logger.info(f"🎯 [{self.profile_name}] Нет пользователей и живых потоков - завершаем работу!")
                    work_finished = True
                    break

                await asyncio.sleep(0.5)  # Увеличили интервал для снижения нагрузки

            except Exception as e:
                logger.error(f"[{self.profile_name}] Ошибка главного цикла: {e}")
                await asyncio.sleep(1)

        # ПРИНУДИТЕЛЬНОЕ завершение всех потоков
        logger.info(f"[{self.profile_name}] Завершаем все оставшиеся потоки...")

        for thread in self.chat_threads:
            if thread.is_alive():
                try:
                    # Устанавливаем флаг остановки
                    self.stop_flag.set()
                    # Ждем завершения с таймаутом
                    thread.join(timeout=10)

                    # Если поток все еще жив - принудительно завершаем
                    if thread.is_alive():
                        logger.warning(
                            f"[{self.profile_name}] Поток {thread.name} не завершился, принудительно останавливаем")
                        # В Python нет способа принудительно убить поток, но устанавливаем флаг
                except Exception as e:
                    logger.error(f"[{self.profile_name}] Ошибка завершения потока {thread.name}: {e}")

        try:
            # Освобождаем все аккаунты
            released_count = self.account_manager.release_all_module_accounts(f"admin_inviter_{self.profile_name}")
            if released_count > 0:
                logger.info(f"[{self.profile_name}] Освобождено аккаунтов: {released_count}")
        except Exception as e:
            logger.error(f"[{self.profile_name}] Ошибка освобождения аккаунтов при завершении: {e}")

        logger.success(f"[{self.profile_name}] ✅ Главный цикл работы завершен успешно!")

    async def _start_chats(self):
        """Запуск потоков чатов"""
        ready_chat_list = list(self.ready_chats)

        if not ready_chat_list:
            logger.error(f"[{self.profile_name}] Нет готовых чатов для запуска")
            return

        for i, chat_link in enumerate(ready_chat_list, 1):
            try:
                thread = ChatWorkerThread(chat_id=i, chat_link=chat_link, parent=self)
                thread.start()
                self.chat_threads.append(thread)
                logger.success(
                    f"[{self.profile_name}]-[Поток-{i}] Запущен чат: {chat_link} (Админ: {self.chat_admins.get(chat_link, ChatAdmin('Неизвестен')).name})")
            except Exception as e:
                logger.error(f"[{self.profile_name}] Ошибка запуска чата {chat_link}: {e}")

    async def _execute_admin_command(self, command: AdminCommand):
        """Выполнение команды от воркера с правильным админом для чата"""
        try:
            if command.chat_link not in self.ready_chats:
                logger.error(f"[{self.profile_name}] Чат {command.chat_link} не готов для работы с потоками")
                command.response_queue.put(False)
                return

            chat_admin = self.chat_admins.get(command.chat_link)
            if not chat_admin or not chat_admin.is_ready:
                logger.error(f"[{self.profile_name}] Админ для чата {command.chat_link} не готов")
                command.response_queue.put(False)
                return

            if command.action == "GRANT_RIGHTS":
                from .admin_rights_manager import grant_worker_rights_directly
                chat_entity = await chat_admin.account.client.get_entity(command.chat_link)
                success = await grant_worker_rights_directly(
                    main_admin=chat_admin.account,
                    chat_entity=chat_entity,
                    worker_user_id=command.worker_user_id,
                    worker_user_access_hash=command.worker_access_hash,
                    worker_name=command.worker_name,
                    worker_username=command.username,
                )
                command.response_queue.put(success)
                if success:
                    logger.success(
                        f"[{self.profile_name}] Права выданы воркеру {command.worker_name} админом {chat_admin.name}")
                else:
                    pass

            elif command.action == "REVOKE_RIGHTS":
                from .admin_rights_manager import revoke_worker_rights_directly
                chat_entity = await chat_admin.account.client.get_entity(command.chat_link)
                await revoke_worker_rights_directly(
                    main_admin_client=chat_admin.account.client,
                    chat_entity=chat_entity,
                    worker_user_id=command.worker_user_id,
                    worker_name=command.worker_name,
                    worker_username=command.username,
                )
                command.response_queue.put(True)

        except Exception as e:
            logger.error(f"[{self.profile_name}] Ошибка выполнения команды {command.action}: {e}")
            command.response_queue.put(False)

    async def _cleanup(self):
        """ОПТИМИЗИРОВАННАЯ очистка без лишнего сохранения"""
        try:
            try:
                module_name = f"admin_inviter_{self.profile_name}"
                released_count = self.account_manager.release_all_module_accounts(module_name)
            except Exception as e:
                logger.error(f"[{self.profile_name}] Ошибка освобождения аккаунтов при очистке: {e}")

            for chat_link, chat_admin in self.chat_admins.items():
                if chat_admin.account:
                    try:
                        if chat_admin.account.client and chat_admin.account.client.is_connected():
                            await chat_admin.account.disconnect()
                            logger.info(f"[{self.profile_name}] Отключен админ {chat_admin.name}")
                    except Exception as e:
                        logger.error(f"[{self.profile_name}] Ошибка отключения админа {chat_admin.name}: {e}")

        except Exception as e:
            logger.error(f"[{self.profile_name}] Ошибка в _cleanup: {e}")

    def graceful_stop(self):
        """Корректная остановка всего профиля с ожиданием потоков"""
        if self.shutdown_in_progress:
            logger.warning(f"[{self.profile_name}] Остановка уже в процессе...")
            return

        self.shutdown_in_progress = True
        logger.info(f"[{self.profile_name}] 🛑 Начинаем корректную остановку профиля...")

        # 1. Устанавливаем флаг остановки
        self.stop_flag.set()
        logger.info(f"[{self.profile_name}] 🚩 Флаг остановки установлен")

        # 2. Ждем завершения всех потоков чатов
        if self.chat_threads:
            logger.info(f"[{self.profile_name}] ⏳ Ожидаем завершения {len(self.chat_threads)} потоков чатов...")

            for i, chat_thread in enumerate(self.chat_threads, 1):
                if chat_thread.is_alive():
                    logger.info(
                        f"[{self.profile_name}] ⏳ Ожидаем чат-поток {i}/{len(self.chat_threads)}: {chat_thread.chat_link}")
                    chat_thread.join(timeout=120)  # Даем 2 минуты на каждый чат

                    if chat_thread.is_alive():
                        logger.warning(f"[{self.profile_name}] ⚠️ Чат-поток {i} не завершился за 2 минуты")
                    else:
                        logger.success(f"[{self.profile_name}] ✅ Чат-поток {i} корректно завершен")
        else:
            logger.info(f"[{self.profile_name}] ℹ️ Нет чат-потоков для ожидания")

        logger.success(f"[{self.profile_name}] ✅ Корректная остановка профиля завершена!")

    def update_account_stats(self, account_name: str, success: bool = False, spam_block: bool = False,
                             error: bool = False):
        """Обновление статистики"""
        if account_name not in self.account_stats:
            self.account_stats[account_name] = AccountStats(name=account_name)

        stats = self.account_stats[account_name]

        if success:
            stats.invites += 1
            self.total_success += 1
            if (self.config.success_per_account > 0 and stats.invites >= self.config.success_per_account):
                stats.status = 'finished'
                self.finished_accounts.add(account_name)
                self.finished_successfully_accounts.add(account_name)
                self.account_finish_times[account_name] = datetime.now()
                self._mark_account_as_processed(account_name, "достигнут лимит успехов")
                self._update_account_status_in_manager_sync(account_name, "finished")

                from .utils import mark_account_as_finished
                mark_account_as_finished(self, account_name)

        if error:
            stats.errors += 1
            self.total_errors += 1

        if spam_block:
            stats.spam_blocks += 1
            if stats.spam_blocks >= self.config.acc_spam_limit:
                stats.status = 'spam_blocked'
                self.frozen_accounts.add(account_name)

        self.total_processed += 1