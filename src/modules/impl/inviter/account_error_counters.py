# src/modules/impl/inviter/account_error_counters.py
"""
Модуль для управления счетчиками ошибок аккаунтов
Вынесен из admin_inviter.py для лучшей организации кода
"""
from dataclasses import dataclass
from typing import Dict
from loguru import logger
from src.entities.moduls.inviter import *
from datetime import datetime


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
        """ПРАВИЛЬНАЯ логика для мертвых аккаунтов"""
        try:
            # МЕРТВЫЕ аккаунты - больше НИКОГДА не будут работать
            permanently_dead_reasons = {
                'dead', 'frozen', 'missing_files', 'unauthorized'
            }

            # ЗАКОНЧИВШИЕ работу
            finished_work_reasons = {
                'достигнут лимит успехов', 'лимит списаний', 'лимит спам-блоков',
                'лимит блоков инвайтов', 'флуд лимит'
            }

            is_permanently_dead = any(dead_reason in reason for dead_reason in permanently_dead_reasons)
            is_finished_work = any(finished_reason in reason for finished_reason in finished_work_reasons)

            if is_permanently_dead or is_finished_work:
                # НАВСЕГДА исключаем
                self.parent.processed_accounts.add(account_name)

                if is_permanently_dead:
                    logger.error(f"[{self.parent.profile_name}] 💀 Аккаунт {account_name} МЕРТВ: {reason}")
                else:
                    pass

                # КРИТИЧНО: Обновляем статус в менеджере
                self._mark_account_as_dead_in_manager(account_name, reason)
            else:
                logger.warning(f"[{self.parent.profile_name}] ⚠️ Временная проблема: {account_name} - {reason}")

            self.parent.account_finish_times[account_name] = datetime.now()

        except Exception as e:
            logger.error(f"[{self.parent.profile_name}] Ошибка пометки {account_name}: {e}")

    def _mark_account_as_dead_in_manager(self, account_name: str, reason: str):
        """КРИТИЧНО: Помечаем аккаунт как мертвый в AccountManager"""
        try:
            if hasattr(self.parent.account_manager, 'traffic_accounts'):
                if account_name in self.parent.account_manager.traffic_accounts:
                    account_data = self.parent.account_manager.traffic_accounts[account_name]

                    # Определяем новый статус
                    if 'dead' in reason or 'unauthorized' in reason or 'missing_files' in reason:
                        new_status = 'dead'
                    elif 'frozen' in reason:
                        new_status = 'frozen'
                    elif 'флуд' in reason:
                        new_status = 'flood'
                    elif 'лимит успехов' in reason:
                        new_status = 'finished'
                    else:
                        new_status = 'dead'

                    # КРИТИЧНО: Меняем статус
                    old_status = account_data.status
                    account_data.status = new_status
                    account_data.is_busy = False
                    account_data.busy_by = None

                    logger.debug(
                        f"[{self.parent.profile_name}] 📝 AccountManager: {account_name} {old_status} -> {new_status}")

        except Exception as e:
            logger.error(f"[{self.parent.profile_name}] Ошибка обновления статуса {account_name}: {e}")

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