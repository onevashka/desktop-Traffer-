# src/modules/impl/inviter/utils.py
"""
Вспомогательные функции для админ-инвайтера
ОБНОВЛЕНО: Добавлена поддержка подготовки главного админа
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
    """Получает свежие аккаунты с фильтрацией"""
    clean_expired_accounts(parent_process)

    all_accounts = parent_process.account_manager.get_free_accounts(module_name, count * 2)
    if not all_accounts:
        logger.warning(f"⚠️ AccountManager не предоставил аккаунты")
        return []

    fresh_accounts = []
    filtered_count = 0

    for account in all_accounts:
        account_name = account.name

        # Фильтруем проблемные аккаунты
        if (account_name in parent_process.finished_accounts or
                account_name in parent_process.frozen_accounts or
                account_name in parent_process.blocked_accounts or
                parent_process.account_mover.is_account_moved(account_name)):
            parent_process.account_manager.release_account(account_name, module_name)
            filtered_count += 1
            continue

        fresh_accounts.append(account)
        if len(fresh_accounts) >= count:
            break

    # Возвращаем лишние
    for account in all_accounts[len(fresh_accounts):]:
        parent_process.account_manager.release_account(account.name, module_name)

    logger.info(f"✅ Получено свежих аккаунтов: {len(fresh_accounts)} (отфильтровано: {filtered_count})")
    return fresh_accounts


def clean_expired_accounts(parent_process):
    """Очищает истекшие аккаунты (24 часа)"""
    now = datetime.now()
    expired = []

    for account_name, finish_time in parent_process.account_finish_times.items():
        if now - finish_time >= timedelta(hours=24):
            expired.append(account_name)

    for account_name in expired:
        parent_process.finished_accounts.discard(account_name)
        del parent_process.account_finish_times[account_name]
        logger.info(f"♻️ Аккаунт {account_name} снова доступен")


def load_main_admin_account(parent_process):
    """Загрузка главного админа"""
    try:
        profile_folder = Path(parent_process.profile_data['folder_path'])
        admins_folder = profile_folder / "Админы"

        session_file = admins_folder / f"{parent_process.main_admin_account_name}.session"
        json_file = admins_folder / f"{parent_process.main_admin_account_name}.json"

        if not session_file.exists() or not json_file.exists():
            logger.error(f"❌ Файлы главного админа не найдены")
            return None

        from src.accounts.impl.account import Account
        account = Account(session_path=session_file, json_path=json_file)

        logger.info(f"✅ Главный админ загружен: {parent_process.main_admin_account_name}")
        return account

    except Exception as e:
        logger.error(f"❌ Ошибка загрузки главного админа: {e}")
        return None


def determine_account_problem(error: Exception) -> str:
    """Определение типа проблемы аккаунта"""
    error_text = str(error).lower()

    if any(keyword in error_text for keyword in ['flood', 'spam', 'rate limit']):
        return 'frozen'
    elif any(keyword in error_text for keyword in ['connection', 'timeout', 'network']):
        return 'connection_failed'
    elif any(keyword in error_text for keyword in ['unauthorized', 'auth', 'session']):
        return 'unauthorized'
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
    """Проверка лимитов чата"""
    if parent_process.config.success_per_chat > 0:
        return chat_success < parent_process.config.success_per_chat
    return True


def check_account_limits(parent_process, account_name: str, invites_count: int) -> bool:
    """Проверка лимитов аккаунта"""
    # Глобальный статус
    account_stats = parent_process.account_stats.get(account_name)
    if account_stats and account_stats.status in ['finished', 'spam_blocked']:
        return False

    # Лимит инвайтов
    if parent_process.config.success_per_account > 0:
        return invites_count < parent_process.config.success_per_account

    return True


def mark_account_as_finished(parent_process, account_name: str):
    """Пометка аккаунта как отработанного"""
    finish_time = datetime.now()
    parent_process.account_finish_times[account_name] = finish_time
    parent_process.finished_accounts.add(account_name)

    next_available = finish_time + timedelta(hours=24)

def print_final_stats(parent_process):
    """Финальная статистика"""
    logger.info("=" * 50)
    logger.info(f"📊 ИТОГОВАЯ СТАТИСТИКА: {parent_process.profile_name}")
    logger.info(f"   Обработано: {parent_process.total_processed}")
    logger.info(f"   Успешно: {parent_process.total_success}")
    logger.info(f"   Ошибок: {parent_process.total_errors}")

    if parent_process.total_processed > 0:
        success_rate = (parent_process.total_success / parent_process.total_processed) * 100
        logger.info(f"   Успешность: {success_rate:.1f}%")

    logger.info(f"   Отработанных аккаунтов: {len(parent_process.finished_accounts)}")
    logger.info(f"   Замороженных аккаунтов: {len(parent_process.frozen_accounts)}")
    logger.info(f"   Заблокированных аккаунтов: {len(parent_process.blocked_accounts)}")
    logger.info("=" * 50)


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


# НОВАЯ ФУНКЦИЯ: Безопасное отключение аккаунта
async def safe_disconnect_account(account, account_name: str, loop=None):
    """Безопасно отключает аккаунт"""
    try:
        await account.disconnect()
        logger.debug(f"🔌 Аккаунт {account_name} отключен")
        return True
    except Exception as e:
        logger.warning(f"⚠️ Ошибка отключения аккаунта {account_name}: {e}")
        return False


# НОВАЯ ФУНКЦИЯ: Получение замещающего аккаунта
def get_replacement_account(parent_process, module_name: str):
    """Получает замещающий аккаунт для замены проблемного"""
    try:
        replacement_accounts = get_fresh_accounts(parent_process, module_name, 1)
        if replacement_accounts:
            return replacement_accounts[0]
        return None
    except Exception as e:
        logger.error(f"❌ Ошибка получения замещающего аккаунта: {e}")
        return None


# НОВАЯ ФУНКЦИЯ: Обработка проблемного аккаунта с заменой
async def handle_and_replace_account(parent_process, account_name: str, account_data, error: Exception,
                                     module_name: str):
    """
    Обрабатывает проблемный аккаунт и возвращает замещающий

    Returns:
        tuple: (replacement_account, success)
    """
    try:
        logger.error(f"🚨 [{parent_process.profile_name}] Обработка проблемного аккаунта: {account_name}")
        logger.error(f"   Ошибка: {error}")

        # 1. Определяем тип проблемы
        problem_type = determine_account_problem(error)

        # 2. Отключаем аккаунт если возможно
        if account_data and hasattr(account_data, 'account'):
            await safe_disconnect_account(account_data.account, account_name, parent_process.main_loop)

        # 3. Освобождаем в менеджере
        parent_process.account_manager.release_account(account_name, module_name)
        logger.info(f"🔓 [{parent_process.profile_name}] Аккаунт {account_name} освобожден в менеджере")

        # 4. Перемещаем файлы через AccountMover
        success = parent_process.account_mover.move_account(account_name, problem_type)

        if success:
            logger.success(
                f"✅ [{parent_process.profile_name}] Аккаунт {account_name} перемещен в папку '{problem_type}'")
        else:
            logger.error(f"❌ [{parent_process.profile_name}] Не удалось переместить аккаунт {account_name}")

        # 5. Добавляем в соответствующие списки
        if problem_type == 'frozen':
            parent_process.frozen_accounts.add(account_name)
        else:
            parent_process.blocked_accounts.add(account_name)

        # 6. КЛЮЧЕВОЕ: Получаем замещающий аккаунт
        replacement_account = get_replacement_account(parent_process, module_name)

        if replacement_account:
            logger.success(f"🔄 [{parent_process.profile_name}] Получен замещающий аккаунт: {replacement_account.name}")
            return replacement_account, True
        else:
            logger.warning(f"⚠️ [{parent_process.profile_name}] Нет доступных замещающих аккаунтов")
            return None, True  # Успешно обработали, но замены нет

    except Exception as e:
        logger.error(f"❌ [{parent_process.profile_name}] Критическая ошибка обработки аккаунта {account_name}: {e}")
        return None, False


# НОВЫЕ ФУНКЦИИ: Для подготовки главного админа

async def verify_main_admin_rights(main_admin_client, chat_link: str) -> bool:
    """
    Проверяет, что главный админ действительно имеет права в чате

    Args:
        main_admin_client: Клиент главного админа
        chat_link: Ссылка на чат

    Returns:
        bool: True если главный админ имеет необходимые права
    """
    try:
        from telethon.tl.functions.channels import GetParticipantRequest

        chat_entity = await main_admin_client.get_entity(chat_link)
        me = await main_admin_client.get_me()

        # Получаем информацию о своих правах в чате
        participant = await main_admin_client(GetParticipantRequest(
            channel=chat_entity,
            participant=me
        ))

        # Проверяем, что у нас есть права админа
        if hasattr(participant.participant, 'admin_rights'):
            admin_rights = participant.participant.admin_rights
            if admin_rights and admin_rights.add_admins:
                return True

        logger.warning(f"⚠️ Главный админ НЕ имеет права в {chat_link}")
        return False

    except Exception as e:
        logger.error(f"❌ Ошибка проверки прав главного админа в {chat_link}: {e}")
        return False


async def wait_for_main_admin_rights(main_admin_client, chat_link: str, timeout_seconds: int = 60) -> bool:
    """
    Ожидает получения прав главным админом в чате

    Args:
        main_admin_client: Клиент главного админа
        chat_link: Ссылка на чат
        timeout_seconds: Максимальное время ожидания

    Returns:
        bool: True если права получены в течение timeout
    """
    logger.info(f"⏳ Ожидание прав главного админа в {chat_link} (макс. {timeout_seconds} сек)")

    start_time = datetime.now()
    check_interval = 5  # Проверяем каждые 5 секунд

    while (datetime.now() - start_time).total_seconds() < timeout_seconds:
        if await verify_main_admin_rights(main_admin_client, chat_link):
            logger.success(f"✅ Права главного админа подтверждены в {chat_link}")
            return True

        logger.info(
            f"⏳ Ждем права главного админа в {chat_link}... (осталось {timeout_seconds - int((datetime.now() - start_time).total_seconds())} сек)")
        await asyncio.sleep(check_interval)

    logger.error(f"❌ Таймаут ожидания прав главного админа в {chat_link}")
    return False


async def ensure_main_admin_ready_in_chat(main_admin_account, admin_rights_manager, chat_link: str) -> bool:
    """
    Обеспечивает полную готовность главного админа в чате

    1. Заходит в группу
    2. Получает права от бота
    3. Проверяет права

    Args:
        main_admin_account: Аккаунт главного админа
        admin_rights_manager: Менеджер прав
        chat_link: Ссылка на чат

    Returns:
        bool: True если главный админ полностью готов
    """
    try:

        # Шаг 1: Заход в группу
        join_result = await main_admin_account.join(chat_link)

        if join_result == "FROZEN_ACCOUNT":
            logger.error(f"❌ Главный админ заморожен!")
            return False
        elif join_result not in ["SUCCESS", "ALREADY_PARTICIPANT"]:
            logger.error(f"❌ Главный админ не смог зайти в {chat_link}: {join_result}")
            return False

        # Шаг 2: Небольшая пауза для стабилизации
        await asyncio.sleep(3)

        # Шаг 3: Получение user_id главного админа
        me = await main_admin_account.client.get_me()
        main_admin_user_id = me.id
        main_admin_name = main_admin_account.session_path.stem

        chat_entity = await main_admin_account.client.get_input_entity(chat_link)
        chat = await main_admin_account.client.get_entity(chat_entity)
        chat_id = getattr(chat, 'id', None)

        # Шаг 4: Бот выдает права
        rights_granted = await admin_rights_manager.grant_main_admin_rights(
            chat_link=chat_id,
            user_id=main_admin_user_id,
            account_name=main_admin_name
        )

        if not rights_granted:
            logger.error(f"❌ Бот не выдал права главному админу в {chat_link}")
            return False

        # Шаг 5: Ожидание и проверка прав
        rights_confirmed = await wait_for_main_admin_rights(
            main_admin_client=main_admin_account.client,
            chat_link=chat_link,
            timeout_seconds=60
        )

        if not rights_confirmed:
            logger.error(f"❌ Права главного админа не подтверждены в {chat_link}")
            return False
        return True

    except Exception as e:
        logger.error(f"❌ Ошибка подготовки главного админа в {chat_link}: {e}")
        return False


def is_chat_ready_for_workers(parent_process, chat_link: str) -> bool:
    """
    Проверяет готовность чата для воркеров

    Args:
        parent_process: Главный процесс
        chat_link: Ссылка на чат

    Returns:
        bool: True если чат готов для воркеров
    """
    return chat_link in parent_process.ready_chats


def get_ready_chats_count(parent_process) -> int:
    """Возвращает количество готовых чатов"""
    return len(parent_process.ready_chats)


def log_main_admin_preparation_summary(parent_process):
    """Выводит сводку по подготовке главного админа"""
    total_chats = 0
    while not parent_process.chat_queue.empty():
        parent_process.chat_queue.get_nowait()
        total_chats += 1

    # Возвращаем чаты обратно в очередь
    for _ in range(total_chats):
        parent_process.chat_queue.put(f"chat_{_}")  # Временная заглушка

    ready_count = len(parent_process.ready_chats)

    logger.info("=" * 60)
    logger.info("📋 СВОДКА ПОДГОТОВКИ ГЛАВНОГО АДМИНА")
    logger.info("=" * 60)
    logger.info(f"Всего чатов: {total_chats}")
    logger.info(f"Готовых чатов: {ready_count}")
    logger.info(f"Процент готовности: {(ready_count / total_chats * 100):.1f}%" if total_chats > 0 else "0%")

    if ready_count > 0:
        logger.info("Готовые чаты:")
        for i, chat in enumerate(parent_process.ready_chats, 1):
            logger.info(f"  {i}. {chat}")

    logger.info("=" * 60)


# НОВАЯ ФУНКЦИЯ: Валидация готовности системы
def validate_system_readiness(parent_process) -> bool:
    """
    Проверяет готовность всей системы к запуску воркеров

    Returns:
        bool: True если система готова
    """
    checks = {
        "Бот подключен": parent_process.bot_manager is not None,
        "Главный админ подключен": parent_process.main_admin_account is not None,
        "Есть готовые чаты": len(parent_process.ready_chats) > 0,
        "Есть пользователи": not parent_process.user_queue.empty(),
        "Фоновый процессор запущен": parent_process.admin_background_thread is not None
    }

    logger.info("🔍 ПРОВЕРКА ГОТОВНОСТИ СИСТЕМЫ")
    logger.info("-" * 40)

    all_ready = True
    for check_name, status in checks.items():
        status_icon = "✅" if status else "❌"
        logger.info(f"{status_icon} {check_name}")
        if not status:
            all_ready = False

    logger.info("-" * 40)

    if all_ready:
        logger.success("🎉 ВСЯ СИСТЕМА ГОТОВА К ЗАПУСКУ ВОРКЕРОВ!")
    else:
        logger.error("❌ Система НЕ готова. Исправьте проблемы выше.")

    return all_ready


# НОВАЯ ФУНКЦИЯ: Проверка состояния главного админа
async def check_main_admin_health(main_admin_client, chat_links: List[str]) -> Dict[str, bool]:
    """
    Проверяет "здоровье" главного админа во всех чатах

    Args:
        main_admin_client: Клиент главного админа
        chat_links: Список чатов для проверки

    Returns:
        Dict: {chat_link: is_healthy}
    """
    results = {}

    logger.info(f"🩺 Проверка здоровья главного админа в {len(chat_links)} чатах")

    for chat_link in chat_links:
        try:
            # Проверяем подключение и права
            is_healthy = await verify_main_admin_rights(main_admin_client, chat_link)
            results[chat_link] = is_healthy

            status_icon = "✅" if is_healthy else "❌"
            logger.info(f"{status_icon} {chat_link}")

        except Exception as e:
            logger.error(f"❌ Ошибка проверки {chat_link}: {e}")
            results[chat_link] = False

    healthy_count = sum(results.values())
    logger.info(f"🩺 Результат: {healthy_count}/{len(chat_links)} чатов здоровы")

    return results