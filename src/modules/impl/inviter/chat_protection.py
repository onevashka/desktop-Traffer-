# chat_protection.py
"""
Система защиты чата от проблемных ситуаций
Отслеживает последовательные проблемы и останавливает работу при превышении лимитов
"""
from dataclasses import dataclass, field
from typing import Dict, Set, List
from datetime import datetime
from loguru import logger


@dataclass
class ChatProtectionStats:
    """Статистика защиты для отдельного чата"""
    chat_link: str

    # Счетчики последовательных проблем (подряд)
    consecutive_writeoff_accounts: int = 0
    consecutive_spam_accounts: int = 0
    consecutive_freeze_accounts: int = 0
    consecutive_flood_accounts: int = 0  # 🔥 НОВЫЙ счетчик специально для флуда!
    consecutive_unknown_error_accounts: int = 0

    # История последних результатов аккаунтов (для отслеживания "подряд")
    last_account_results: List[str] = field(default_factory=list)
    max_history_size: int = 10  # Храним последние 10 результатов

    # Флаги блокировки
    is_blocked: bool = False
    block_reason: str = ""
    blocked_at: datetime = None

    def add_account_result(self, result_type: str) -> None:
        """Добавляет результат работы аккаунта и обновляет счетчики"""
        self.last_account_results.append(result_type)

        # Ограничиваем размер истории
        if len(self.last_account_results) > self.max_history_size:
            self.last_account_results.pop(0)

        # Обновляем счетчики последовательных проблем
        self._update_consecutive_counters()

    def _update_consecutive_counters(self):
        """Обновляет счетчики последовательных проблем"""
        # Сбрасываем все счетчики
        self.consecutive_writeoff_accounts = 0
        self.consecutive_spam_accounts = 0
        self.consecutive_freeze_accounts = 0
        self.consecutive_flood_accounts = 0  # 🔥 НОВЫЙ сброс
        self.consecutive_unknown_error_accounts = 0

        # Считаем последовательные проблемы с конца списка
        for result in reversed(self.last_account_results):
            if result == "writeoff_limit":
                self.consecutive_writeoff_accounts += 1
                if self.consecutive_writeoff_accounts == 1:
                    # Продолжаем подсчет только writeoff
                    continue
                else:
                    # Если уже начали считать writeoff, проверяем следующий
                    if self.last_account_results[-self.consecutive_writeoff_accounts] != "writeoff_limit":
                        self.consecutive_writeoff_accounts -= 1
                        break
            elif result == "spam_limit":
                self.consecutive_spam_accounts += 1
                if self.consecutive_spam_accounts == 1:
                    continue
                else:
                    if self.last_account_results[-self.consecutive_spam_accounts] != "spam_limit":
                        self.consecutive_spam_accounts -= 1
                        break
            elif result == "frozen":  # 🔥 ИСПРАВЛЕНО: frozen отдельно от flood
                self.consecutive_freeze_accounts += 1
                if self.consecutive_freeze_accounts == 1:
                    continue
                else:
                    if self.last_account_results[-self.consecutive_freeze_accounts] != "frozen":
                        self.consecutive_freeze_accounts -= 1
                        break
            elif result == "flood":  # 🔥 НОВАЯ ОБРАБОТКА: flood отдельно!
                self.consecutive_flood_accounts += 1
                if self.consecutive_flood_accounts == 1:
                    continue
                else:
                    if self.last_account_results[-self.consecutive_flood_accounts] != "flood":
                        self.consecutive_flood_accounts -= 1
                        break
            elif result in ["block_limit", "dead", "unknown_error"]:
                self.consecutive_unknown_error_accounts += 1
                if self.consecutive_unknown_error_accounts == 1:
                    continue
                else:
                    if self.last_account_results[-self.consecutive_unknown_error_accounts] not in ["block_limit",
                                                                                                   "dead",
                                                                                                   "unknown_error"]:
                        self.consecutive_unknown_error_accounts -= 1
                        break
            elif result == "success":
                # При успехе сбрасываем все счетчики
                self.consecutive_writeoff_accounts = 0
                self.consecutive_spam_accounts = 0
                self.consecutive_freeze_accounts = 0
                self.consecutive_flood_accounts = 0  # 🔥 НОВЫЙ сброс!
                self.consecutive_unknown_error_accounts = 0
                break
            else:
                # При любом другом результате прерываем последовательность
                break

    def _count_consecutive_from_end(self, target_types: List[str]) -> int:
        """Подсчитывает количество последовательных результатов определенных типов с конца"""
        count = 0
        for result in reversed(self.last_account_results):
            if result in target_types:
                count += 1
            else:
                break
        return count

    def reset_on_success(self):
        """Сбрасывает счетчики при успешном инвайте"""
        self.consecutive_writeoff_accounts = 0
        self.consecutive_spam_accounts = 0
        self.consecutive_freeze_accounts = 0
        self.consecutive_flood_accounts = 0  # 🔥 НОВЫЙ сброс
        self.consecutive_unknown_error_accounts = 0


class ChatProtectionManager:
    """Менеджер защиты чатов от проблемных ситуаций"""

    def __init__(self, parent):
        self.parent = parent
        self.chat_stats: Dict[str, ChatProtectionStats] = {}
        self.blocked_chats: Set[str] = set()

    def check_chat_protection(self, chat_link: str, account_name: str, finish_reason: str) -> bool:
        """
        🔥 ИСПРАВЛЕННАЯ проверка защиты чата с отдельной обработкой флуда

        Args:
            chat_link: Ссылка на чат
            account_name: Имя аккаунта
            finish_reason: Причина завершения ("writeoff_limit", "spam_limit", "frozen", "flood", "block_limit", "dead", "success")

        Returns:
            True если чат нужно заблокировать, False если можно продолжать
        """
        # Инициализируем статистику если ее нет
        if chat_link not in self.chat_stats:
            self.chat_stats[chat_link] = ChatProtectionStats(chat_link=chat_link)

        stats = self.chat_stats[chat_link]

        # Если чат уже заблокирован
        if stats.is_blocked or chat_link in self.blocked_chats:
            return True

        # Добавляем результат работы аккаунта
        stats.add_account_result(finish_reason)

        # При успехе сбрасываем счетчики
        if finish_reason == "success":
            stats.reset_on_success()
            logger.info(f"[{self.parent.profile_name}] ✅ Успех в чате {chat_link} - сбрасываем счетчики защиты")
            return False

        # Пересчитываем последовательные проблемы более точно
        stats.consecutive_writeoff_accounts = stats._count_consecutive_from_end(["writeoff_limit"])
        stats.consecutive_spam_accounts = stats._count_consecutive_from_end(["spam_limit"])
        stats.consecutive_freeze_accounts = stats._count_consecutive_from_end(["frozen"])
        stats.consecutive_flood_accounts = stats._count_consecutive_from_end(["flood"])  # 🔥 ОТДЕЛЬНЫЙ подсчет флуда!
        stats.consecutive_unknown_error_accounts = stats._count_consecutive_from_end(
            ["block_limit", "dead", "unknown_error"])

        # Проверяем лимиты
        config = self.parent.config

        # 🔥 НОВАЯ ПРОВЕРКА: Специальная защита от флуда - ЖЕСТКИЙ лимит 2 аккаунта!
        if stats.consecutive_flood_accounts >= 2:  # 🔥 ЖЕСТКО ЗАДАЕМ 2 флуд аккаунта подряд
            self._block_chat(chat_link, stats,
                             f"🚫 ФЛУД ЗАЩИТА: {stats.consecutive_flood_accounts} аккаунтов подряд получили FloodWait (лимит: 2)")
            return True

        # Проверка лимита списаний
        if config.chat_writeoff_accounts > 0 and stats.consecutive_writeoff_accounts >= config.chat_writeoff_accounts:
            self._block_chat(chat_link, stats,
                             f"Превышен лимит последовательных списаний: {stats.consecutive_writeoff_accounts} подряд (лимит: {config.chat_writeoff_accounts})")
            return True

        # Проверка лимита спама
        if config.chat_spam_accounts > 0 and stats.consecutive_spam_accounts >= config.chat_spam_accounts:
            self._block_chat(chat_link, stats,
                             f"Превышен лимит последовательных спам-блоков: {stats.consecutive_spam_accounts} подряд (лимит: {config.chat_spam_accounts})")
            return True

        # Проверка лимита заморозок (БЕЗ флуда)
        if config.chat_freeze_accounts > 0 and stats.consecutive_freeze_accounts >= config.chat_freeze_accounts:
            self._block_chat(chat_link, stats,
                             f"Превышен лимит последовательных заморозок: {stats.consecutive_freeze_accounts} подряд (лимит: {config.chat_freeze_accounts})")
            return True

        # Проверка лимита неизвестных ошибок
        if config.chat_unknown_error_accounts > 0 and stats.consecutive_unknown_error_accounts >= config.chat_unknown_error_accounts:
            self._block_chat(chat_link, stats,
                             f"Превышен лимит последовательных ошибок: {stats.consecutive_unknown_error_accounts} подряд (лимит: {config.chat_unknown_error_accounts})")
            return True

        # 🔥 УЛУЧШЕННОЕ логирование с флудом
        logger.info(f"[{self.parent.profile_name}] Защита чата {chat_link}: "
                    f"🚫 Флуд: {stats.consecutive_flood_accounts}/2, "  # 🔥 ПОКАЗЫВАЕМ флуд отдельно!
                    f"📝 Списания: {stats.consecutive_writeoff_accounts}/{config.chat_writeoff_accounts}, "
                    f"🚫 Спам: {stats.consecutive_spam_accounts}/{config.chat_spam_accounts}, "
                    f"🥶 Заморозки: {stats.consecutive_freeze_accounts}/{config.chat_freeze_accounts}, "
                    f"💥 Ошибки: {stats.consecutive_unknown_error_accounts}/{config.chat_unknown_error_accounts}")

        return False

    def _block_chat(self, chat_link: str, stats: ChatProtectionStats, reason: str):
        """Блокирует чат"""
        stats.is_blocked = True
        stats.block_reason = reason
        stats.blocked_at = datetime.now()
        self.blocked_chats.add(chat_link)

        logger.error(f"🚫 [{self.parent.profile_name}] ЧАТ ЗАБЛОКИРОВАН: {chat_link}")
        logger.error(f"🚫 [{self.parent.profile_name}] Причина: {reason}")
        logger.error(f"🚫 [{self.parent.profile_name}] История последних результатов: {stats.last_account_results[-5:]}")

        self.parent.record_stopped_chat(chat_link, reason)

        # Устанавливаем флаг остановки для всех потоков этого чата
        if hasattr(self.parent, 'chat_threads'):
            for thread in self.parent.chat_threads:
                if hasattr(thread, 'chat_link') and thread.chat_link == chat_link:
                    logger.info(f"[{self.parent.profile_name}] Останавливаем поток чата {chat_link}")
                    # Можно установить специальный флаг для потока
                    if hasattr(thread, 'stop_chat_flag'):
                        thread.stop_chat_flag.set()

    def is_chat_blocked(self, chat_link: str) -> bool:
        """Проверяет, заблокирован ли чат"""
        return chat_link in self.blocked_chats

    def get_chat_stats(self, chat_link: str) -> ChatProtectionStats:
        """Получает статистику защиты чата"""
        if chat_link not in self.chat_stats:
            self.chat_stats[chat_link] = ChatProtectionStats(chat_link=chat_link)
        return self.chat_stats[chat_link]

    def get_protection_report(self) -> str:
        """🔥 ОБНОВЛЕННЫЙ отчет по защите чатов с флудом"""
        report = []
        report.append("=" * 50)
        report.append("ОТЧЕТ ПО ЗАЩИТЕ ЧАТОВ")
        report.append("=" * 50)

        for chat_link, stats in self.chat_stats.items():
            report.append(f"\nЧат: {chat_link}")
            report.append(f"  Статус: {'🚫 ЗАБЛОКИРОВАН' if stats.is_blocked else '✅ Активен'}")
            if stats.is_blocked:
                report.append(f"  Причина блокировки: {stats.block_reason}")
                report.append(f"  Время блокировки: {stats.blocked_at}")
            report.append(f"  Последовательные списания: {stats.consecutive_writeoff_accounts}")
            report.append(f"  Последовательные спам-блоки: {stats.consecutive_spam_accounts}")
            report.append(f"  Последовательные заморозки: {stats.consecutive_freeze_accounts}")
            report.append(f"  🔥 Последовательные флуды: {stats.consecutive_flood_accounts}")  # 🔥 НОВАЯ строка!
            report.append(f"  Последовательные ошибки: {stats.consecutive_unknown_error_accounts}")
            report.append(f"  История (последние 5): {stats.last_account_results[-5:]}")

        if self.blocked_chats:
            report.append("\n" + "=" * 50)
            report.append(f"ВСЕГО ЗАБЛОКИРОВАНО ЧАТОВ: {len(self.blocked_chats)}")
            for chat in self.blocked_chats:
                report.append(f"  - {chat}")

        return "\n".join(report)