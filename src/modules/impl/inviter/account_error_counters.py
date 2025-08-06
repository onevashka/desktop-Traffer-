# src/modules/impl/inviter/account_error_counters.py
"""
Модуль для управления счетчиками ошибок аккаунтов
Вынесен из admin_inviter.py для лучшей организации кода
"""
from dataclasses import dataclass
from typing import Dict
from loguru import logger
from src.entities.moduls.inviter import *


class AccountErrorManager:
    """Менеджер для управления ошибками аккаунтов"""

    def __init__(self, parent_process):
        self.parent = parent_process
        self.error_counters: Dict[str, AccountErrorCounters] = {}

    def get_counters(self, account_name: str) -> AccountErrorCounters:
        """Получение счетчиков ошибок для аккаунта"""
        if account_name not in self.error_counters:
            self.error_counters[account_name] = AccountErrorCounters()
        return self.error_counters[account_name]

    def check_error_limits(self, account_name: str, error_type: str) -> bool:
        """
        Проверка лимитов ошибок для аккаунта

        Args:
            account_name: Имя аккаунта
            error_type: Тип ошибки (spam_block, writeoff, block_invite, success)

        Returns:
            True если аккаунт нужно завершить, False если можно продолжать
        """
        counters = self.get_counters(account_name)
        config = self.parent.config
        profile_name = self.parent.profile_name

        if error_type == "spam_block":
            counters.consecutive_spam_blocks += 1
            counters.reset_writeoffs()
            counters.reset_block_invites()

            if counters.consecutive_spam_blocks >= config.acc_spam_limit:
                logger.error(
                    f"[{profile_name}] Аккаунт {account_name} превысил лимит спам-блоков: {counters.consecutive_spam_blocks}/{config.acc_spam_limit}")
                return True

        elif error_type == "writeoff":
            counters.consecutive_writeoffs += 1
            counters.reset_spam_blocks()
            counters.reset_block_invites()

            if counters.consecutive_writeoffs >= config.acc_writeoff_limit:
                logger.error(
                    f"[{profile_name}] Аккаунт {account_name} превысил лимит списаний: {counters.consecutive_writeoffs}/{config.acc_writeoff_limit}")
                return True

        elif error_type == "block_invite":
            counters.consecutive_block_invites += 1
            counters.reset_spam_blocks()
            counters.reset_writeoffs()

            if counters.consecutive_block_invites >= config.acc_block_invite_limit:
                logger.error(
                    f"[{profile_name}] Аккаунт {account_name} превысил лимит блоков инвайтов: {counters.consecutive_block_invites}/{config.acc_block_invite_limit}")
                return True

        elif error_type == "success":
            # При успехе сбрасываем все счетчики
            counters.reset_all()

        return False

    def mark_account_as_processed(self, account_name: str, reason: str):
        """
        Помечает аккаунт как обработанный чтобы он больше не использовался
        """
        self.parent.processed_accounts.add(account_name)
        logger.debug(f"[{self.parent.profile_name}] Аккаунт {account_name} помечен как обработанный: {reason}")

    def update_account_status_in_manager_sync(self, account_name: str, new_status: str):
        """
        Синхронное обновление статуса в менеджере
        """
        try:
            account_manager = self.parent.account_manager
            profile_name = self.parent.profile_name

            if hasattr(account_manager, 'traffic_accounts'):
                if account_name in account_manager.traffic_accounts:
                    account_data = account_manager.traffic_accounts[account_name]

                    old_status = account_data.status
                    account_data.status = new_status
                    account_data.is_busy = False
                    account_data.busy_by = None

                else:
                    logger.warning(
                        f"[{profile_name}] Аккаунт {account_name} не найден в traffic_accounts менеджера")
            else:
                logger.warning(f"[{profile_name}] У менеджера нет traffic_accounts")
        except Exception as e:
            logger.error(f"[{self.parent.profile_name}] КРИТИЧЕСКАЯ ошибка обновления статуса в менеджере: {e}")