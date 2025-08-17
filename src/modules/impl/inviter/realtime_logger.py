# src/modules/impl/inviter/realtime_logger.py
import threading
from datetime import datetime
from pathlib import Path
from loguru import logger
from src.entities.moduls.inviter import InviteUser, UserStatus
from .cumulative_reports import CumulativeReportsManager

class RealtimeLogger:
    """Система последовательного логирования в реальном времени"""

    def __init__(self, profile_name: str, profile_folder: Path):
        self.profile_name = profile_name
        self.profile_folder = profile_folder
        self.lock = threading.Lock()

        # Создаем папку для отчетов
        self.reports_folder = profile_folder / "Отчеты"
        self.reports_folder.mkdir(exist_ok=True)

        # Файлы для записи
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.success_report_file = self.reports_folder / f"Успешные_приглашения_{timestamp}.txt"
        self.users_status_file = profile_folder / "База юзеров.txt"  # СУЩЕСТВУЮЩИЙ файл!

        # Инициализируем отчет успешных приглашений
        self._init_success_report()

        # 🔥 НОВОЕ: Инициализируем систему накопительных отчетов
        self.cumulative_reports = CumulativeReportsManager(profile_name, profile_folder)

        logger.success(f"[{self.profile_name}] Система реального времени готова")
        logger.info(f"[{self.profile_name}] Отчет успехов: {self.success_report_file}")
        logger.info(f"[{self.profile_name}] Обновляем статусы в: {self.users_status_file}")

    def _init_success_report(self):
        """Создает заголовок файла успешных приглашений"""
        try:
            with open(self.success_report_file, 'w', encoding='utf-8') as f:
                f.write(f"🎯 ПОСЛЕДОВАТЕЛЬНЫЙ ОТЧЕТ УСПЕШНЫХ ПРИГЛАШЕНИЙ\n")
                f.write(f"=" * 70 + "\n")
                f.write(f"📋 Профиль: {self.profile_name}\n")
                f.write(f"🕐 Начало: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"=" * 70 + "\n\n")
                f.write(f"ФОРМАТ: [ВРЕМЯ] ЧАТ -> @username (аккаунт)\n")
                f.write(f"-" * 70 + "\n\n")
                f.flush()
        except Exception as e:
            logger.error(f"[{self.profile_name}] Ошибка создания отчета: {e}")

    def log_successful_invite(self, username: str, chat_link: str, account_name: str):
        """КРИТИЧЕСКАЯ ФУНКЦИЯ: Записывает успешное приглашение НЕМЕДЛЕННО"""
        with self.lock:
            try:
                timestamp = datetime.now().strftime('%H:%M:%S')
                chat_display = chat_link.replace('https://t.me/', '').replace('http://t.me/', '')

                log_line = f"[{timestamp}] {chat_display} -> @{username} ({account_name})\n"

                # НЕМЕДЛЕННАЯ запись в файл
                with open(self.success_report_file, 'a', encoding='utf-8') as f:
                    f.write(log_line)
                    f.flush()  # Принудительное сохранение на диск

                self.cumulative_reports.log_successful_invite(username, chat_link)

                # Логируем краткую сводку накопительной статистики
                stats = self.cumulative_reports.get_stats_summary()
                logger.debug(
                    f"[{self.profile_name}] 📊 Накопительная статистика: сегодня {stats['daily_total']}, всего {stats['total_invites']}")

            except Exception as e:
                logger.error(f"[{self.profile_name}] ОШИБКА записи успеха: {e}")

    def update_user_status_immediately(self, user: InviteUser):
        """
        КРИТИЧЕСКАЯ ФУНКЦИЯ: Обновляет статус пользователя ПРЯМО В СУЩЕСТВУЮЩЕМ ФАЙЛЕ
        """
        with self.lock:
            try:
                username = user.username.lstrip('@')
                status_text = self._get_status_text(user.status)

                if not self.users_status_file.exists():
                    logger.warning(f"[{self.profile_name}] Файл 'База юзеров.txt' не найден!")
                    return

                # ЧИТАЕМ все строки файла
                with open(self.users_status_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()

                # ОБНОВЛЯЕМ статус напротив нужного пользователя
                updated = False
                for i, line in enumerate(lines):
                    line_stripped = line.strip()

                    # Пропускаем пустые строки и комментарии
                    if not line_stripped or line_stripped.startswith('#'):
                        continue

                    # Проверяем, это ли наш пользователь (сравниваем первое слово)
                    first_word = line_stripped.split()[0].lstrip('@')

                    if first_word == username:
                        # НАЙДЕН! Обновляем строку добавляя статус
                        if '|' in line_stripped:
                            # Уже есть статус, заменяем
                            parts = line_stripped.split('|')
                            parts[1] = status_text  # Заменяем статус
                            lines[i] = '|'.join(parts) + '\n'
                        else:
                            # Нет статуса, добавляем
                            lines[i] = f"{line_stripped}|{status_text}\n"

                        updated = True
                        break

                if updated:
                    # ПЕРЕЗАПИСЫВАЕМ весь файл с обновленным статусом
                    with open(self.users_status_file, 'w', encoding='utf-8') as f:
                        f.writelines(lines)
                        f.flush()  # Принудительное сохранение

                else:
                    logger.warning(f"[{self.profile_name}] ⚠️ Пользователь @{username} не найден в базе!")

            except Exception as e:
                logger.error(f"[{self.profile_name}] ОШИБКА обновления статуса: {e}")

    def _get_status_text(self, status: UserStatus) -> str:
        """Преобразует статус в текст"""
        status_mapping = {
            UserStatus.INVITED: "УСПЕШНО_ДОБАВЛЕН",
            UserStatus.ERROR: "СПИСАНИЕ",  # Для общих ошибок/списаний
            UserStatus.PRIVACY: "ПРИВАТНЫЕ_ОГРАНИЧЕНИЯ",
            UserStatus.SPAM_BLOCK: "СПАМ_БЛОК",
            UserStatus.ALREADY_IN: "УЖЕ_В_ЧАТЕ",
            UserStatus.NOT_FOUND: "НЕ_НАЙДЕН"
        }
        return status_mapping.get(status, "БЛОК_ИНВАЙТА")  # По умолчанию для неизвестных ошибок

    def finalize_report(self, total_processed: int, total_successful: int):
        """🔥 УСИЛЕННОЕ ЗАВЕРШЕНИЕ: Завершает отчет с принудительным сохранением"""
        with self.lock:
            try:
                # 1. Завершаем последовательный отчет (как было)
                with open(self.success_report_file, 'a', encoding='utf-8') as f:
                    f.write(f"\n" + "=" * 70 + "\n")
                    f.write(f"🏁 ИТОГОВАЯ СТАТИСТИКА\n")
                    f.write(f"🕐 Завершено: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"📊 Всего обработано: {total_processed}\n")
                    f.write(f"✅ Успешно добавлено: {total_successful}\n")
                    success_rate = (total_successful / total_processed * 100) if total_processed > 0 else 0
                    f.write(f"📈 Процент успеха: {success_rate:.1f}%\n")
                    f.write(f"=" * 70 + "\n")
                    f.flush()

                # 🔥 2. КРИТИЧНО: Принудительное сохранение накопительных данных
                logger.info(f"[{self.profile_name}] 💾 Выполняем финальное сохранение накопительных данных...")

                save_success = self.cumulative_reports.force_save_and_verify()

                if save_success:
                    logger.success(f"[{self.profile_name}] ✅ Накопительные данные надежно сохранены")
                else:
                    logger.error(f"[{self.profile_name}] ❌ ПРОБЛЕМЫ с сохранением накопительных данных!")

                    # Показываем диагностику
                    integrity_report = self.cumulative_reports.get_data_integrity_report()
                    logger.error(f"[{self.profile_name}] 🔍 Диагностика целостности: {integrity_report}")

                # 3. Генерируем финальные версии накопительных отчетов
                self.cumulative_reports._generate_daily_report()
                self.cumulative_reports._generate_total_report()

                # 4. Показываем итоговую сводку накопительной статистики
                stats = self.cumulative_reports.get_stats_summary()
                logger.success(f"[{self.profile_name}] 📊 НАКОПИТЕЛЬНАЯ СТАТИСТИКА:")
                logger.success(
                    f"[{self.profile_name}] 📅 За сегодня: {stats['daily_total']} приглашений в {stats['daily_chats']} чатов")
                logger.success(
                    f"[{self.profile_name}] 📈 За все время: {stats['total_invites']} приглашений в {stats['total_chats']} чатов")

                logger.success(f"[{self.profile_name}] 📄 ВСЕ ОТЧЕТЫ ЗАВЕРШЕНЫ!")

            except Exception as e:
                logger.error(f"[{self.profile_name}] ❌ Ошибка завершения отчета: {e}")

                # В случае ошибки пытаемся хотя бы сохранить накопительные данные
                try:
                    logger.warning(f"[{self.profile_name}] 🆘 Аварийное сохранение накопительных данных...")
                    self.cumulative_reports.force_save_and_verify()
                except Exception as emergency_error:
                    logger.error(f"[{self.profile_name}] ❌ Аварийное сохранение не удалось: {emergency_error}")