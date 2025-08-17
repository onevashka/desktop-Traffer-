# src/modules/impl/inviter/cumulative_reports.py
"""
Система накопительных отчетов:
- Суточные отчеты (обновляются каждый день)
- Итоговый отчет (накапливает данные за все время)
"""

import json
import threading
from datetime import datetime, date
from pathlib import Path
from loguru import logger
from typing import Dict, Set, List
from collections import defaultdict


class CumulativeReportsManager:
    """Менеджер накопительных отчетов (суточные + итоговый)"""

    def __init__(self, profile_name: str, profile_folder: Path):
        self.profile_name = profile_name
        self.profile_folder = profile_folder
        self.lock = threading.Lock()

        # Создаем папки для отчетов
        self.daily_folder = profile_folder / "Отчет_за_сутки"
        self.total_folder = profile_folder / "Итог"
        self.daily_folder.mkdir(exist_ok=True)
        self.total_folder.mkdir(exist_ok=True)

        # Файлы для хранения данных
        self.daily_data_file = self.daily_folder / ".daily_data.json"
        self.total_data_file = self.total_folder / ".total_data.json"

        # Текущая дата для отслеживания смены дня
        self.current_date = date.today()

        # Структуры данных в памяти
        self.daily_data = {
            "date": self.current_date.strftime("%d_%m_%Y"),
            "total_invites": 0,
            "chats": {}  # chat_link -> {"count": int, "users": [username1, username2, ...]}
        }

        self.total_data = {
            "profile_name": profile_name,
            "total_invites": 0,
            "first_invite_date": None,
            "last_invite_date": None,
            "chats": {}  # chat_link -> {"count": int, "users": [username1, username2, ...]}
        }

        # Загружаем существующие данные
        self._load_existing_data()

        # Генерируем начальные отчеты
        self._generate_daily_report()
        self._generate_total_report()

        logger.success(f"[{self.profile_name}] 📊 Система накопительных отчетов готова")
        logger.info(f"[{self.profile_name}] 📅 Суточный отчет: {self.daily_folder}")
        logger.info(f"[{self.profile_name}] 📈 Итоговый отчет: {self.total_folder}")

    def _load_existing_data(self):
        """🔥 УСИЛЕННАЯ ЗАГРУЗКА: Загружает существующие данные при запуске с полной защитой"""
        try:
            logger.info(f"[{self.profile_name}] 🔄 Загружаем существующие данные...")

            # 1. ЗАГРУЗКА ИТОГОВЫХ ДАННЫХ
            total_loaded = False
            if self.total_data_file.exists():
                try:
                    with open(self.total_data_file, 'r', encoding='utf-8') as f:
                        saved_total = json.load(f)

                    # Проверяем целостность данных
                    if self._validate_total_data(saved_total):
                        self.total_data.update(saved_total)
                        total_loaded = True
                        logger.success(
                            f"[{self.profile_name}] 📈 Загружены итоговые данные: {self.total_data['total_invites']} приглашений")
                    else:
                        logger.warning(f"[{self.profile_name}] ⚠️ Итоговые данные повреждены, начинаем с чистого листа")

                except (json.JSONDecodeError, UnicodeDecodeError, IOError) as e:
                    logger.error(f"[{self.profile_name}] ❌ Поврежден файл итоговых данных: {e}")
                    # Создаем резервную копию поврежденного файла
                    backup_file = self.total_data_file.with_suffix('.json.backup')
                    try:
                        import shutil
                        shutil.copy2(self.total_data_file, backup_file)
                        logger.info(f"[{self.profile_name}] 💾 Создана резервная копия: {backup_file}")
                    except Exception:
                        pass

            if not total_loaded:
                logger.info(f"[{self.profile_name}] 🆕 Создаем новые итоговые данные (первый запуск или восстановление)")
                # Данные уже инициализированы в __init__

            # 2. ЗАГРУЗКА СУТОЧНЫХ ДАННЫХ
            daily_loaded = False
            if self.daily_data_file.exists():
                try:
                    with open(self.daily_data_file, 'r', encoding='utf-8') as f:
                        saved_daily = json.load(f)

                    # Проверяем целостность данных
                    if self._validate_daily_data(saved_daily):
                        # Проверяем, не сменился ли день
                        saved_date = saved_daily.get("date", "")
                        current_date_str = self.current_date.strftime("%d_%m_%Y")

                        if saved_date == current_date_str:
                            # Тот же день - загружаем данные
                            self.daily_data.update(saved_daily)
                            daily_loaded = True
                            logger.success(
                                f"[{self.profile_name}] 📅 Загружены суточные данные: {self.daily_data['total_invites']} приглашений за сегодня")
                        else:
                            # Новый день - архивируем старые данные и начинаем заново
                            if saved_date:
                                logger.info(
                                    f"[{self.profile_name}] 🌅 Обнаружена смена дня: {saved_date} → {current_date_str}")
                                self._archive_previous_day(saved_daily)
                            logger.info(f"[{self.profile_name}] 🆕 Начинаем новый день с чистой суточной статистикой")
                    else:
                        logger.warning(f"[{self.profile_name}] ⚠️ Суточные данные повреждены, начинаем день заново")

                except (json.JSONDecodeError, UnicodeDecodeError, IOError) as e:
                    logger.error(f"[{self.profile_name}] ❌ Поврежден файл суточных данных: {e}")
                    # Создаем резервную копию поврежденного файла
                    backup_file = self.daily_data_file.with_suffix('.json.backup')
                    try:
                        import shutil
                        shutil.copy2(self.daily_data_file, backup_file)
                        logger.info(f"[{self.profile_name}] 💾 Создана резервная копия: {backup_file}")
                    except Exception:
                        pass

            if not daily_loaded:
                logger.info(
                    f"[{self.profile_name}] 🆕 Создаем новые суточные данные (первый запуск дня или восстановление)")
                # Данные уже инициализированы в __init__

            # 3. ПРИНУДИТЕЛЬНОЕ СОЗДАНИЕ НАЧАЛЬНЫХ JSON ФАЙЛОВ
            self._ensure_json_files_exist()

            logger.success(f"[{self.profile_name}] ✅ Загрузка данных завершена успешно")

        except Exception as e:
            logger.error(f"[{self.profile_name}] ❌ Критическая ошибка загрузки данных: {e}")
            logger.info(f"[{self.profile_name}] 🔧 Инициализируем систему с нуля...")
            # В случае критической ошибки - работаем с чистыми данными
            # Они уже инициализированы в __init__

    def _validate_total_data(self, data: Dict) -> bool:
        """🔥 НОВОЕ: Проверяет целостность итоговых данных"""
        try:
            required_keys = ["profile_name", "total_invites", "chats"]

            # Проверяем наличие обязательных ключей
            for key in required_keys:
                if key not in data:
                    logger.warning(f"[{self.profile_name}] ⚠️ Отсутствует ключ '{key}' в итоговых данных")
                    return False

            # Проверяем типы данных
            if not isinstance(data["total_invites"], int) or data["total_invites"] < 0:
                logger.warning(f"[{self.profile_name}] ⚠️ Некорректный total_invites в итоговых данных")
                return False

            if not isinstance(data["chats"], dict):
                logger.warning(f"[{self.profile_name}] ⚠️ Некорректная структура chats в итоговых данных")
                return False

            # Проверяем структуру чатов
            for chat_link, chat_data in data["chats"].items():
                if not isinstance(chat_data, dict):
                    continue
                if "count" not in chat_data or "users" not in chat_data:
                    logger.warning(
                        f"[{self.profile_name}] ⚠️ Некорректная структура чата {chat_link} в итоговых данных")
                    return False
                if not isinstance(chat_data["count"], int) or not isinstance(chat_data["users"], list):
                    logger.warning(
                        f"[{self.profile_name}] ⚠️ Некорректные типы данных чата {chat_link} в итоговых данных")
                    return False

            return True

        except Exception as e:
            logger.error(f"[{self.profile_name}] ❌ Ошибка валидации итоговых данных: {e}")
            return False

    def _validate_daily_data(self, data: Dict) -> bool:
        """🔥 НОВОЕ: Проверяет целостность суточных данных"""
        try:
            required_keys = ["date", "total_invites", "chats"]

            # Проверяем наличие обязательных ключей
            for key in required_keys:
                if key not in data:
                    logger.warning(f"[{self.profile_name}] ⚠️ Отсутствует ключ '{key}' в суточных данных")
                    return False

            # Проверяем типы данных
            if not isinstance(data["total_invites"], int) or data["total_invites"] < 0:
                logger.warning(f"[{self.profile_name}] ⚠️ Некорректный total_invites в суточных данных")
                return False

            if not isinstance(data["chats"], dict):
                logger.warning(f"[{self.profile_name}] ⚠️ Некорректная структура chats в суточных данных")
                return False

            # Проверяем формат даты
            if not isinstance(data["date"], str) or len(data["date"]) != 10:
                logger.warning(f"[{self.profile_name}] ⚠️ Некорректный формат даты в суточных данных")
                return False

            return True

        except Exception as e:
            logger.error(f"[{self.profile_name}] ❌ Ошибка валидации суточных данных: {e}")
            return False

    def _ensure_json_files_exist(self):
        """🔥 НОВОЕ: Убеждается что JSON файлы существуют и содержат корректные данные"""
        try:
            # Проверяем и создаем файл итоговых данных
            if not self.total_data_file.exists() or self.total_data_file.stat().st_size == 0:
                logger.info(f"[{self.profile_name}] 📄 Создаем файл итоговых данных...")
                self._save_total_data_to_json()

            # Проверяем и создаем файл суточных данных
            if not self.daily_data_file.exists() or self.daily_data_file.stat().st_size == 0:
                logger.info(f"[{self.profile_name}] 📄 Создаем файл суточных данных...")
                self._save_daily_data_to_json()

        except Exception as e:
            logger.error(f"[{self.profile_name}] ❌ Ошибка создания JSON файлов: {e}")

    def _archive_previous_day(self, old_daily_data: Dict):
        """Архивирует данные предыдущего дня"""
        try:
            old_date = old_daily_data.get("date", "неизвестно")
            archive_file = self.daily_folder / f"За_сутки_{old_date}.txt"

            # Генерируем отчет для предыдущего дня
            lines = []
            lines.append(f"📅 ОТЧЕТ ЗА СУТКИ - {old_date.replace('_', '.')}")
            lines.append("=" * 50)
            lines.append(f"📋 Профиль: {self.profile_name}")
            lines.append(f"✅ Всего приглашений за сутки: {old_daily_data.get('total_invites', 0)}")
            lines.append("")

            chats_data = old_daily_data.get('chats', {})
            if chats_data:
                lines.append("📱 СТАТИСТИКА ПО ЧАТАМ:")
                lines.append("")

                for chat_link, chat_info in chats_data.items():
                    chat_display = chat_link.replace('https://t.me/', '').replace('http://t.me/', '')
                    count = chat_info.get('count', 0)
                    users = chat_info.get('users', [])

                    lines.append(f"🔗 ЧАТ: {chat_display}")
                    lines.append(f"📊 Приглашено: {count} пользователей")

                    if users:
                        lines.append("👥 ПОЛЬЗОВАТЕЛИ:")
                        for username in users:
                            lines.append(f"   @{username}")

                    lines.append("")
                    lines.append("-" * 40)
                    lines.append("")
            else:
                lines.append("❌ За эти сутки никого не пригласили")

            # Сохраняем архивный файл
            with open(archive_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))

            logger.info(f"[{self.profile_name}] 📦 Данные за {old_date} архивированы: {archive_file}")

        except Exception as e:
            logger.error(f"[{self.profile_name}] ❌ Ошибка архивирования: {e}")
        """Архивирует данные предыдущего дня"""
        try:
            old_date = old_daily_data.get("date", "неизвестно")
            archive_file = self.daily_folder / f"За_сутки_{old_date}.txt"

            # Генерируем отчет для предыдущего дня
            lines = []
            lines.append(f"📅 ОТЧЕТ ЗА СУТКИ - {old_date.replace('_', '.')}")
            lines.append("=" * 50)
            lines.append(f"📋 Профиль: {self.profile_name}")
            lines.append(f"✅ Всего приглашений за сутки: {old_daily_data.get('total_invites', 0)}")
            lines.append("")

            chats_data = old_daily_data.get('chats', {})
            if chats_data:
                lines.append("📱 СТАТИСТИКА ПО ЧАТАМ:")
                lines.append("")

                for chat_link, chat_info in chats_data.items():
                    chat_display = chat_link.replace('https://t.me/', '').replace('http://t.me/', '')
                    count = chat_info.get('count', 0)
                    users = chat_info.get('users', [])

                    lines.append(f"🔗 ЧАТ: {chat_display}")
                    lines.append(f"📊 Приглашено: {count} пользователей")

                    if users:
                        lines.append("👥 ПОЛЬЗОВАТЕЛИ:")
                        for username in users:
                            lines.append(f"   @{username}")

                    lines.append("")
                    lines.append("-" * 40)
                    lines.append("")
            else:
                lines.append("❌ За эти сутки никого не пригласили")

            # Сохраняем архивный файл
            with open(archive_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))

            logger.info(f"[{self.profile_name}] 📦 Данные за {old_date} архивированы: {archive_file}")

        except Exception as e:
            logger.error(f"[{self.profile_name}] ❌ Ошибка архивирования: {e}")

    def log_successful_invite(self, username: str, chat_link: str):
        """
        🔥 УСИЛЕННАЯ ФУНКЦИЯ: Записывает успешное приглашение в ОБА отчета с максимальной надежностью
        """
        with self.lock:
            try:
                # Проверяем смену дня
                self._check_day_change()

                username_clean = username.lstrip('@')
                current_time = datetime.now()

                logger.debug(
                    f"[{self.profile_name}] 📊 Обновляем накопительную статистику: @{username_clean} → {chat_link}")

                # ОБНОВЛЯЕМ СУТОЧНЫЕ ДАННЫЕ
                self._update_daily_data(username_clean, chat_link)

                # ОБНОВЛЯЕМ ИТОГОВЫЕ ДАННЫЕ
                self._update_total_data(username_clean, chat_link, current_time)

                # 🔥 КРИТИЧНО: СОХРАНЯЕМ В JSON НЕМЕДЛЕННО (с проверкой ошибок)
                save_success = False
                retry_count = 3

                for attempt in range(retry_count):
                    try:
                        self._save_data_to_json()
                        save_success = True
                        break
                    except Exception as save_error:
                        logger.warning(
                            f"[{self.profile_name}] ⚠️ Попытка {attempt + 1}/{retry_count} сохранения не удалась: {save_error}")
                        if attempt < retry_count - 1:
                            import time
                            time.sleep(0.1)  # Небольшая задержка перед повтором

                if not save_success:
                    logger.error(
                        f"[{self.profile_name}] ❌ НЕ УДАЛОСЬ СОХРАНИТЬ накопительные данные после {retry_count} попыток!")
                    # Продолжаем работу, но данные могут быть потеряны при сбое

                # ГЕНЕРИРУЕМ TXT ОТЧЕТЫ (даже если JSON не сохранился)
                try:
                    self._generate_daily_report()
                    self._generate_total_report()
                except Exception as report_error:
                    logger.error(f"[{self.profile_name}] ❌ Ошибка генерации TXT отчетов: {report_error}")

                # Логируем успешное обновление
                stats = self.get_stats_summary()
                logger.debug(
                    f"[{self.profile_name}] ✅ Накопительная статистика: сегодня {stats['daily_total']}, всего {stats['total_invites']}")

            except Exception as e:
                logger.error(f"[{self.profile_name}] ❌ КРИТИЧЕСКАЯ ОШИБКА обновления накопительной статистики: {e}")
                # Система продолжит работать, но данные этого приглашения могут быть потеряны

    def _check_day_change(self):
        """Проверяет смену дня и архивирует данные при необходимости"""
        today = date.today()

        if today != self.current_date:
            logger.info(f"[{self.profile_name}] 🌅 Обнаружена смена дня: {self.current_date} → {today}")

            # Архивируем данные вчерашнего дня
            old_daily_data = self.daily_data.copy()
            self._archive_previous_day(old_daily_data)

            # Сбрасываем суточные данные
            self.current_date = today
            self.daily_data = {
                "date": today.strftime("%d_%m_%Y"),
                "total_invites": 0,
                "chats": {}
            }

            logger.info(f"[{self.profile_name}] 🔄 Суточная статистика сброшена для нового дня")

    def _update_daily_data(self, username: str, chat_link: str):
        """Обновляет суточные данные"""
        # Увеличиваем общий счетчик
        self.daily_data["total_invites"] += 1

        # Обновляем данные по чату
        if chat_link not in self.daily_data["chats"]:
            self.daily_data["chats"][chat_link] = {
                "count": 0,
                "users": []
            }

        chat_data = self.daily_data["chats"][chat_link]
        chat_data["count"] += 1

        # Добавляем пользователя если его еще нет в этом чате за сегодня
        if username not in chat_data["users"]:
            chat_data["users"].append(username)

    def _update_total_data(self, username: str, chat_link: str, current_time: datetime):
        """Обновляет итоговые данные"""
        # Увеличиваем общий счетчик
        self.total_data["total_invites"] += 1

        # Обновляем даты
        current_date_str = current_time.strftime("%Y-%m-%d %H:%M:%S")
        if not self.total_data["first_invite_date"]:
            self.total_data["first_invite_date"] = current_date_str
        self.total_data["last_invite_date"] = current_date_str

        # Обновляем данные по чату
        if chat_link not in self.total_data["chats"]:
            self.total_data["chats"][chat_link] = {
                "count": 0,
                "users": []
            }

        chat_data = self.total_data["chats"][chat_link]
        chat_data["count"] += 1

        # Добавляем пользователя если его еще нет в этом чате за все время
        if username not in chat_data["users"]:
            chat_data["users"].append(username)

    def _save_data_to_json(self):
        """🔥 УСИЛЕННОЕ СОХРАНЕНИЕ: Сохраняет данные в JSON файлы с проверкой ошибок"""
        # Сохраняем оба файла отдельно для лучшей надежности
        self._save_daily_data_to_json()
        self._save_total_data_to_json()

    def _save_daily_data_to_json(self):
        """🔥 НОВОЕ: Надежное сохранение суточных данных"""
        try:
            # Сначала сохраняем во временный файл
            temp_file = self.daily_data_file.with_suffix('.json.tmp')

            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(self.daily_data, f, ensure_ascii=False, indent=2)
                f.flush()  # Принудительная запись

            # Проверяем что временный файл записался корректно
            if temp_file.exists() and temp_file.stat().st_size > 0:
                # Атомарно заменяем основной файл
                if self.daily_data_file.exists():
                    backup_file = self.daily_data_file.with_suffix('.json.bak')
                    import shutil
                    shutil.move(self.daily_data_file, backup_file)

                import shutil
                shutil.move(temp_file, self.daily_data_file)

                # Удаляем старый бэкап если все прошло успешно
                backup_file = self.daily_data_file.with_suffix('.json.bak')
                if backup_file.exists():
                    backup_file.unlink()

            else:
                raise IOError("Временный файл суточных данных пуст или не создался")

        except Exception as e:
            logger.error(f"[{self.profile_name}] ❌ Ошибка сохранения суточных данных: {e}")
            # Очищаем временный файл при ошибке
            temp_file = self.daily_data_file.with_suffix('.json.tmp')
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except:
                    pass

    def _save_total_data_to_json(self):
        """🔥 НОВОЕ: Надежное сохранение итоговых данных"""
        try:
            # Сначала сохраняем во временный файл
            temp_file = self.total_data_file.with_suffix('.json.tmp')

            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(self.total_data, f, ensure_ascii=False, indent=2)
                f.flush()  # Принудительная запись

            # Проверяем что временный файл записался корректно
            if temp_file.exists() and temp_file.stat().st_size > 0:
                # Атомарно заменяем основной файл
                if self.total_data_file.exists():
                    backup_file = self.total_data_file.with_suffix('.json.bak')
                    import shutil
                    shutil.move(self.total_data_file, backup_file)

                import shutil
                shutil.move(temp_file, self.total_data_file)

                # Удаляем старый бэкап если все прошло успешно
                backup_file = self.total_data_file.with_suffix('.json.bak')
                if backup_file.exists():
                    backup_file.unlink()

            else:
                raise IOError("Временный файл итоговых данных пуст или не создался")

        except Exception as e:
            logger.error(f"[{self.profile_name}] ❌ Ошибка сохранения итоговых данных: {e}")
            # Очищаем временный файл при ошибке
            temp_file = self.total_data_file.with_suffix('.json.tmp')
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except:
                    pass

    def _generate_daily_report(self):
        """Генерирует суточный TXT отчет"""
        try:
            date_str = self.daily_data["date"]
            report_file = self.daily_folder / f"За_сутки_{date_str}.txt"

            lines = []
            lines.append(f"📅 ОТЧЕТ ЗА СУТКИ - {date_str.replace('_', '.')}")
            lines.append("=" * 50)
            lines.append(f"📋 Профиль: {self.profile_name}")
            lines.append(f"✅ Всего приглашений за сутки: {self.daily_data['total_invites']}")
            lines.append(f"🕐 Последнее обновление: {datetime.now().strftime('%H:%M:%S')}")
            lines.append("")

            if self.daily_data["chats"]:
                lines.append("📱 СТАТИСТИКА ПО ЧАТАМ:")
                lines.append("")

                # Сортируем чаты по количеству приглашений (убывание)
                sorted_chats = sorted(
                    self.daily_data["chats"].items(),
                    key=lambda x: x[1]["count"],
                    reverse=True
                )

                for chat_link, chat_info in sorted_chats:
                    chat_display = chat_link.replace('https://t.me/', '').replace('http://t.me/', '')
                    count = chat_info["count"]
                    users = chat_info["users"]

                    lines.append(f"🔗 ЧАТ: {chat_display}")
                    lines.append(f"📊 Приглашено: {count} пользователей")

                    if users:
                        lines.append("👥 ПОЛЬЗОВАТЕЛИ:")
                        for username in users:
                            lines.append(f"   @{username}")

                    lines.append("")
                    lines.append("-" * 40)
                    lines.append("")
            else:
                lines.append("❌ За сегодня никого не пригласили")

            # Записываем файл
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))

        except Exception as e:
            logger.error(f"[{self.profile_name}] ❌ Ошибка генерации суточного отчета: {e}")

    def _generate_total_report(self):
        """Генерирует итоговый TXT отчет"""
        try:
            report_file = self.total_folder / "Итог.txt"

            lines = []
            lines.append(f"📈 ИТОГОВЫЙ ОТЧЕТ ПРОФИЛЯ")
            lines.append("=" * 60)
            lines.append(f"📋 Профиль: {self.profile_name}")
            lines.append(f"✅ Всего приглашений: {self.total_data['total_invites']}")

            if self.total_data["first_invite_date"]:
                lines.append(f"🎯 Первое приглашение: {self.total_data['first_invite_date']}")
            if self.total_data["last_invite_date"]:
                lines.append(f"🕐 Последнее приглашение: {self.total_data['last_invite_date']}")

            lines.append(f"🔄 Последнее обновление: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            lines.append("")

            if self.total_data["chats"]:
                lines.append("📱 СТАТИСТИКА ПО ЧАТАМ ЗА ВСЕ ВРЕМЯ:")
                lines.append("")

                # Сортируем чаты по количеству приглашений (убывание)
                sorted_chats = sorted(
                    self.total_data["chats"].items(),
                    key=lambda x: x[1]["count"],
                    reverse=True
                )

                for chat_link, chat_info in sorted_chats:
                    chat_display = chat_link.replace('https://t.me/', '').replace('http://t.me/', '')
                    count = chat_info["count"]
                    users = chat_info["users"]

                    lines.append(f"🔗 ЧАТ: {chat_display}")
                    lines.append(f"📊 Всего приглашено: {count} пользователей")

                    if users:
                        lines.append(f"👥 ПОЛЬЗОВАТЕЛИ ({len(users)} чел.):")
                        # Ограничиваем количество показываемых пользователей для читаемости
                        display_users = users[:100]  # Показываем первые 100
                        for username in display_users:
                            lines.append(f"   @{username}")

                        if len(users) > 100:
                            lines.append(f"   ... и еще {len(users) - 100} пользователей")

                    lines.append("")
                    lines.append("-" * 50)
                    lines.append("")
            else:
                lines.append("❌ Пока никого не пригласили")

            lines.append("")
            lines.append("=" * 60)
            lines.append("📊 Эта статистика накапливается за все время существования профиля")

            # Записываем файл
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))

        except Exception as e:
            logger.error(f"[{self.profile_name}] ❌ Ошибка генерации итогового отчета: {e}")

    def get_stats_summary(self) -> Dict:
        """Возвращает краткую сводку для логирования"""
        return {
            "daily_total": self.daily_data["total_invites"],
            "daily_chats": len(self.daily_data["chats"]),
            "total_invites": self.total_data["total_invites"],
            "total_chats": len(self.total_data["chats"])
        }

    def force_save_and_verify(self) -> bool:
        """🔥 НОВОЕ: Принудительное сохранение с проверкой целостности (для завершения работы)"""
        with self.lock:
            try:
                logger.info(f"[{self.profile_name}] 💾 Принудительное сохранение накопительных данных...")

                # Сохраняем данные
                self._save_data_to_json()

                # Проверяем что файлы действительно сохранились и читаются
                total_ok = False
                daily_ok = False

                if self.total_data_file.exists():
                    try:
                        with open(self.total_data_file, 'r', encoding='utf-8') as f:
                            test_data = json.load(f)
                        if self._validate_total_data(test_data):
                            total_ok = True
                    except Exception as e:
                        logger.error(f"[{self.profile_name}] ❌ Проверка итогового файла не удалась: {e}")

                if self.daily_data_file.exists():
                    try:
                        with open(self.daily_data_file, 'r', encoding='utf-8') as f:
                            test_data = json.load(f)
                        if self._validate_daily_data(test_data):
                            daily_ok = True
                    except Exception as e:
                        logger.error(f"[{self.profile_name}] ❌ Проверка суточного файла не удалась: {e}")

                if total_ok and daily_ok:
                    logger.success(f"[{self.profile_name}] ✅ Накопительные данные сохранены и проверены")
                    return True
                else:
                    logger.error(
                        f"[{self.profile_name}] ❌ Проблемы с сохранением: итоговые={total_ok}, суточные={daily_ok}")
                    return False

            except Exception as e:
                logger.error(f"[{self.profile_name}] ❌ Ошибка принудительного сохранения: {e}")
                return False

    def get_data_integrity_report(self) -> Dict:
        """🔥 НОВОЕ: Отчет о целостности данных для диагностики"""
        report = {
            "total_file_exists": self.total_data_file.exists(),
            "daily_file_exists": self.daily_data_file.exists(),
            "total_file_size": 0,
            "daily_file_size": 0,
            "total_data_valid": False,
            "daily_data_valid": False,
            "memory_total_invites": self.total_data["total_invites"],
            "memory_daily_invites": self.daily_data["total_invites"]
        }

        try:
            if report["total_file_exists"]:
                report["total_file_size"] = self.total_data_file.stat().st_size
                with open(self.total_data_file, 'r', encoding='utf-8') as f:
                    test_data = json.load(f)
                report["total_data_valid"] = self._validate_total_data(test_data)
        except:
            pass

        try:
            if report["daily_file_exists"]:
                report["daily_file_size"] = self.daily_data_file.stat().st_size
                with open(self.daily_data_file, 'r', encoding='utf-8') as f:
                    test_data = json.load(f)
                report["daily_data_valid"] = self._validate_daily_data(test_data)
        except:
            pass

        return report