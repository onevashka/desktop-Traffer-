# src/modules/impl/inviter/utils.py
"""
Вспомогательные функции для админ-инвайтера
"""

import asyncio
import queue
import threading
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from loguru import logger
from pathlib import Path

from src.entities.moduls.inviter import InviteUser, UserStatus, AccountStats
from .account_mover import AccountMover

# Импорты Telethon
from telethon.tl.functions.channels import InviteToChannelRequest
from telethon.tl.functions.users import GetFullUserRequest
from telethon.tl.functions.messages import GetCommonChatsRequest
from telethon.errors import (
    UsernameInvalidError, UsernameNotOccupiedError,
    PeerFloodError, FloodWaitError,
    UserPrivacyRestrictedError, UserNotMutualContactError,
    ChatAdminRequiredError, ChatWriteForbiddenError,
    UsersTooMuchError, ChannelsTooMuchError,
    UserDeactivatedBanError, UserDeactivatedError,
    AuthKeyUnregisteredError, SessionRevokedError,
    ChannelPrivateError, ChannelInvalidError
)


def get_fresh_accounts(parent_process, module_name: str, count: int) -> List:
    """Получает свежие (не отработанные и не проблемные) аккаунты"""
    # Проверяем и очищаем аккаунты с истекшей 24-часовой меткой
    clean_expired_accounts(parent_process)

    # Получаем аккаунты от менеджера
    all_accounts = parent_process.account_manager.get_free_accounts(module_name, count * 3)  # Берем с большим запасом

    if not all_accounts:
        logger.warning(f"[{parent_process.profile_name}] AccountManager не предоставил аккаунты")
        return []

    # Фильтруем проблемные и отработанные аккаунты
    fresh_accounts = []
    filtered_out = []

    for account in all_accounts:
        account_name = account.name
        should_skip = False
        skip_reason = ""

        # Проверяем не перемещен ли аккаунт
        if hasattr(parent_process, 'account_mover') and parent_process.account_mover.is_account_moved(account_name):
            should_skip = True
            skip_reason = "перемещен"

        # Проверяем не отработан ли аккаунт
        elif account_name in parent_process.finished_accounts:
            should_skip = True
            skip_reason = "отработан"

        # Проверяем не заморожен ли аккаунт
        elif account_name in parent_process.frozen_accounts:
            should_skip = True
            skip_reason = "заморожен"

        # НОВОЕ: Проверяем локальный черный список
        elif hasattr(parent_process, 'blocked_accounts') and account_name in parent_process.blocked_accounts:
            should_skip = True
            skip_reason = "заблокирован локально"

        if should_skip:
            # Возвращаем проблемный аккаунт обратно
            parent_process.account_manager.release_account(account_name, module_name)
            filtered_out.append(f"{account_name} ({skip_reason})")
            logger.debug(f"[{parent_process.profile_name}] Аккаунт {account_name} {skip_reason}, пропускаем")
            continue

        # Аккаунт подходит
        fresh_accounts.append(account)
        if len(fresh_accounts) >= count:
            break

    # Возвращаем лишние аккаунты
    for account in all_accounts[len(fresh_accounts):]:
        if account not in fresh_accounts:
            parent_process.account_manager.release_account(account.name, module_name)

    if filtered_out:
        logger.info(f"[{parent_process.profile_name}] Отфильтровано аккаунтов: {len(filtered_out)}")
        logger.debug(f"   Детали: {', '.join(filtered_out[:5])}" + ("..." if len(filtered_out) > 5 else ""))

    logger.info(
        f"[{parent_process.profile_name}] Получено свежих аккаунтов: {len(fresh_accounts)} из {len(all_accounts)} запрошенных")
    return fresh_accounts


def clean_expired_accounts(parent_process):
    """Очищает аккаунты с истекшей 24-часовой меткой"""
    now = datetime.now()
    expired = []

    for account_name, finish_time in parent_process.account_finish_times.items():
        if now - finish_time >= timedelta(hours=24):
            expired.append(account_name)

    for account_name in expired:
        parent_process.finished_accounts.discard(account_name)
        del parent_process.account_finish_times[account_name]
        logger.info(f"[{parent_process.profile_name}] Аккаунт {account_name} снова доступен (прошло 24 часа)")


def load_main_admin_account(parent_process):
    """Загружает объект Account главного админа из папки Админы"""
    try:
        profile_folder = Path(parent_process.profile_data['folder_path'])
        admins_folder = profile_folder / "Админы"

        # Ищем файлы аккаунта
        session_file = admins_folder / f"{parent_process.main_admin_account_name}.session"
        json_file = admins_folder / f"{parent_process.main_admin_account_name}.json"

        if not session_file.exists():
            logger.error(f"❌ Не найден session файл: {session_file}")
            return None

        if not json_file.exists():
            logger.error(f"❌ Не найден JSON файл: {json_file}")
            return None

        # Создаем аккаунт напрямую
        from src.accounts.impl.account import Account
        account = Account(
            session_path=session_file,
            json_path=json_file
        )

        logger.info(f"✅ Загружен главный админ из папки Админы: {parent_process.main_admin_account_name}")
        return account

    except Exception as e:
        logger.error(f"❌ Ошибка загрузки главного админа: {e}")
        return None


def determine_account_problem(error: Exception) -> str:
    """Определяет тип проблемы аккаунта по ошибке"""
    error_text = str(error).lower()

    # Заморозка/спам
    if any(keyword in error_text for keyword in ['flood', 'spam', 'rate limit', 'peer_flood']):
        return 'frozen'

    # Проблемы с подключением
    elif any(keyword in error_text for keyword in ['connection', 'connect', 'timeout', 'network']):
        return 'connection_failed'

    # Не авторизован
    elif any(keyword in error_text for keyword in ['unauthorized', 'not authorized', 'auth', 'session']):
        return 'unauthorized'

    # По умолчанию - мертвый
    else:
        return 'dead'


async def initialize_worker_clients(worker_accounts: List, parent_process):
    """Инициализирует клиенты для воркеров"""
    logger.info(f"🔧 Инициализация клиентов для {len(worker_accounts)} воркеров...")

    for account_data in worker_accounts:
        try:
            await account_data.account.create_client()
            logger.debug(f"✅ Клиент создан для воркера: {account_data.name}")
        except Exception as e:
            logger.error(f"❌ Ошибка создания клиента для воркера {account_data.name}: {e}")


def check_chat_limits(parent_process, chat_success: int) -> bool:
    """Проверяет лимиты для чата"""
    # Лимит успешных для чата
    if parent_process.config.success_per_chat > 0:
        if chat_success >= parent_process.config.success_per_chat:
            return False
    return True


def check_account_limits(parent_process, account_name: str, invites_count: int) -> bool:
    """Проверяет лимиты для аккаунта"""
    # Проверяем глобальный статус аккаунта
    account_stats = parent_process.account_stats.get(account_name)
    if account_stats:
        if account_stats.status == 'finished':
            return False
        if account_stats.status == 'spam_blocked':
            return False

    # Лимит для аккаунта
    if parent_process.config.success_per_account > 0:
        if invites_count >= parent_process.config.success_per_account:
            return False

    return True


def mark_account_as_finished(parent_process, account_name: str):
    """Помечает аккаунт как отработанный на 24 часа"""
    try:
        finish_time = datetime.now()
        parent_process.account_finish_times[account_name] = finish_time
        next_available = finish_time + timedelta(hours=24)
        logger.info(f"📌 [{parent_process.profile_name}] Аккаунт {account_name} помечен как отработанный")
        logger.info(f"   ⏰ Будет доступен: {next_available.strftime('%Y-%m-%d %H:%M:%S')}")
    except Exception as e:
        logger.error(f"❌ [{parent_process.profile_name}] Ошибка пометки аккаунта {account_name}: {e}")


def print_final_stats(parent_process):
    """Выводит финальную статистику"""
    logger.info("=" * 60)
    logger.info(f"[{parent_process.profile_name}] 📊 ИТОГОВАЯ СТАТИСТИКА:")
    logger.info(f"[{parent_process.profile_name}] Всего обработано: {parent_process.total_processed}")
    logger.info(f"[{parent_process.profile_name}] Успешных инвайтов: {parent_process.total_success}")
    logger.info(f"[{parent_process.profile_name}] Ошибок: {parent_process.total_errors}")

    if parent_process.total_processed > 0:
        success_rate = (parent_process.total_success / parent_process.total_processed) * 100
        logger.info(f"[{parent_process.profile_name}] Процент успеха: {success_rate:.1f}%")

    # Статистика по аккаунтам
    logger.info(f"\n📊 СТАТИСТИКА ПО АККАУНТАМ:")
    for account_name, stats in parent_process.account_stats.items():
        status_icon = "✅" if stats.status == 'finished' else "⚡" if stats.status == 'working' else "❌"
        logger.info(
            f"   {status_icon} {account_name}: инвайтов={stats.invites}, ошибок={stats.errors}, спамблоков={stats.spam_blocks}, статус={stats.status}")

    if parent_process.finished_accounts:
        logger.info(f"\n🏁 ОТРАБОТАВШИЕ АККАУНТЫ: {len(parent_process.finished_accounts)}")
        for account_name in parent_process.finished_accounts:
            if account_name in parent_process.account_finish_times:
                finish_time = parent_process.account_finish_times[account_name]
                next_available = finish_time + timedelta(hours=24)
                logger.info(f"   - {account_name} (доступен с {next_available.strftime('%H:%M:%S')})")

    if parent_process.frozen_accounts:
        logger.warning(f"\nЗАМОРОЖЕННЫЕ АККАУНТЫ: {len(parent_process.frozen_accounts)}")
        for frozen_account in parent_process.frozen_accounts:
            logger.warning(f"   - {frozen_account}")

    logger.info("=" * 60)


def release_worker_accounts(worker_accounts: List, module_name: str, account_manager):
    """Освобождает список воркер-аккаунтов"""
    released_count = 0

    for account_data in worker_accounts:
        try:
            account_manager.release_account(account_data.name, module_name)
            released_count += 1
        except Exception as e:
            logger.error(f"❌ Ошибка освобождения воркера {account_data.name}: {e}")

    logger.info(f"🔓 Освобождено воркеров: {released_count} из {len(worker_accounts)}")
    return released_count