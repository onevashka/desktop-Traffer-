# src/services/account_report_service.py
"""
Сервис для генерации отчетов по инвайтам аккаунтов
Сканирует все папки аккаунтов и собирает статистику по green_people
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple
from loguru import logger
from src.accounts.impl.utils import load_json_data
from paths import WORK_TRAFFER_FOLDER


class AccountReportService:
    """Сервис для создания отчетов по инвайтам аккаунтов"""

    def __init__(self):
        self.base_folder = WORK_TRAFFER_FOLDER
        self.folder_mapping = {
            "Аккаунты": self.base_folder / "Аккаунты",
            "Списанные": self.base_folder / "Списанные",
            "Мертвые": self.base_folder / "Мертвые",
            "Замороженные": self.base_folder / "Замороженные",
            "Спам_блок": self.base_folder / "Спам_блок",
            "Блок_инвайтов": self.base_folder / "Блок_инвайтов",
            "Успешно_отработанные": self.base_folder / "Успешно_отработанные",
            "Флуд": self.base_folder / "Флуд"
        }

    def scan_all_accounts(self) -> Dict[str, List[Tuple[str, int]]]:
        """
        Сканирует все папки аккаунтов и собирает статистику

        Returns:
            Dict[folder_name, List[Tuple[account_name, green_people_count]]]
        """
        report_data = {}
        total_scanned = 0
        total_with_invites = 0

        logger.info("🔍 Начинаем сканирование аккаунтов для отчета...")

        for folder_name, folder_path in self.folder_mapping.items():
            if not folder_path.exists():
                logger.debug(f"📁 Папка {folder_name} не существует: {folder_path}")
                continue

            logger.info(f"📂 Сканируем папку: {folder_name}")
            accounts_data = self._scan_folder(folder_path)

            if accounts_data:
                report_data[folder_name] = accounts_data
                folder_total = len(accounts_data)
                folder_with_invites = sum(1 for _, count in accounts_data if count > 0)

                total_scanned += folder_total
                total_with_invites += folder_with_invites

                logger.info(f"✅ {folder_name}: {folder_total} аккаунтов, {folder_with_invites} с инвайтами")
            else:
                logger.debug(f"📂 {folder_name}: нет аккаунтов")

        logger.success(f"🎯 Сканирование завершено: {total_scanned} аккаунтов, {total_with_invites} с инвайтами")
        return report_data

    def _scan_folder(self, folder_path: Path) -> List[Tuple[str, int]]:
        """
        Сканирует конкретную папку аккаунтов

        Returns:
            List[Tuple[account_name, green_people_count]]
        """
        accounts_data = []

        try:
            # Ищем все JSON файлы аккаунтов
            json_files = list(folder_path.glob("*.json"))

            for json_file in json_files:
                try:
                    account_name = json_file.stem

                    # Загружаем данные аккаунта
                    account_data = load_json_data(json_file)

                    if account_data:
                        # Получаем счетчик green_people
                        green_people = account_data.get('green_people', 0)

                        # Проверяем что это число
                        if not isinstance(green_people, (int, float)):
                            green_people = 0
                        else:
                            green_people = int(green_people)

                        accounts_data.append((account_name, green_people))

                        if green_people > 0:
                            logger.debug(f"  📊 {account_name}: {green_people} инвайтов")

                except Exception as e:
                    logger.warning(f"⚠️ Ошибка чтения аккаунта {json_file.name}: {e}")
                    continue

        except Exception as e:
            logger.error(f"❌ Ошибка сканирования папки {folder_path}: {e}")

        # Сортируем по количеству инвайтов (убывание)
        accounts_data.sort(key=lambda x: x[1], reverse=True)
        return accounts_data

    def generate_report(self, output_path: Path = None) -> str:
        """
        Генерирует полный отчет по аккаунтам

        Args:
            output_path: Путь для сохранения отчета (по умолчанию в папку Инвайт)

        Returns:
            Путь к созданному файлу отчета
        """
        try:
            logger.info("📝 Генерируем отчет по аккаунтам...")

            # Сканируем все аккаунты
            report_data = self.scan_all_accounts()

            # Определяем путь для сохранения
            if output_path is None:
                from paths import WORK_TRAFFER_FOLDER
                reports_folder = WORK_TRAFFER_FOLDER / "Инвайт" / "Отчеты_по_аккаунтам"
                reports_folder.mkdir(parents=True, exist_ok=True)

                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = reports_folder / f"Отчет_по_аккаунтам_{timestamp}.txt"

            # Генерируем содержимое отчета
            report_content = self._build_report_content(report_data)

            # Сохраняем файл
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(report_content)

            logger.success(f"✅ Отчет сохранен: {output_path}")
            return str(output_path)

        except Exception as e:
            logger.error(f"❌ Ошибка генерации отчета: {e}")
            raise

    def _build_report_content(self, report_data: Dict[str, List[Tuple[str, int]]]) -> str:
        """Строит содержимое отчета"""
        lines = []

        # Заголовок отчета
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        lines.append("📊 ОТЧЕТ ПО ИНВАЙТАМ АККАУНТОВ")
        lines.append("=" * 60)
        lines.append(f"🕐 Дата создания: {timestamp}")
        lines.append(f"📁 Источник: {self.base_folder}")
        lines.append("=" * 60)
        lines.append("")

        # Общая статистика
        total_accounts = sum(len(accounts) for accounts in report_data.values())
        total_invites = sum(sum(count for _, count in accounts) for accounts in report_data.values())
        accounts_with_invites = sum(sum(1 for _, count in accounts if count > 0) for accounts in report_data.values())

        lines.append("📈 ОБЩАЯ СТАТИСТИКА:")
        lines.append(f"👥 Всего аккаунтов: {total_accounts:,}")
        lines.append(f"✅ Аккаунтов с инвайтами: {accounts_with_invites:,}")
        lines.append(f"🎯 Общее количество инвайтов: {total_invites:,}")
        if total_accounts > 0:
            avg_invites = total_invites / total_accounts
            lines.append(f"📊 Среднее инвайтов на аккаунт: {avg_invites:.1f}")
        lines.append("")
        lines.append("=" * 60)
        lines.append("")

        # Детализация по папкам
        for folder_name, accounts in report_data.items():
            if not accounts:
                continue

            folder_total = len(accounts)
            folder_invites = sum(count for _, count in accounts)
            folder_with_invites = sum(1 for _, count in accounts if count > 0)

            lines.append(f"📂 {folder_name.upper()}:")
            lines.append(f"   👥 Аккаунтов: {folder_total}")
            lines.append(f"   ✅ С инвайтами: {folder_with_invites}")
            lines.append(f"   🎯 Всего инвайтов: {folder_invites}")
            lines.append("")

            if folder_with_invites > 0:
                # Показываем только аккаунты с инвайтами
                for account_name, invite_count in accounts:
                    if invite_count > 0:
                        lines.append(f"   {account_name} - пригласил {invite_count} пользователей")

                lines.append("")

                # ТОП-3 аккаунта в папке
                top_accounts = accounts[:3]
                if any(count > 0 for _, count in top_accounts):
                    lines.append(f"   🏆 ТОП-3 аккаунта папки:")
                    for i, (account_name, invite_count) in enumerate(top_accounts, 1):
                        if invite_count > 0:
                            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉"
                            lines.append(f"   {medal} {account_name}: {invite_count} инвайтов")
                    lines.append("")
            else:
                lines.append("   ❌ Нет аккаунтов с инвайтами")
                lines.append("")

            lines.append("-" * 40)
            lines.append("")

        # ТОП аккаунтов общий
        all_accounts = []
        for accounts in report_data.values():
            all_accounts.extend(accounts)

        # Сортируем по количеству инвайтов
        all_accounts.sort(key=lambda x: x[1], reverse=True)
        top_performers = [acc for acc in all_accounts[:10] if acc[1] > 0]

        if top_performers:
            lines.append("🏆 ТОП-10 АККАУНТОВ ПО ИНВАЙТАМ:")
            lines.append("")
            for i, (account_name, invite_count) in enumerate(top_performers, 1):
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i:2d}."
                lines.append(f"{medal} {account_name}: {invite_count} инвайтов")
            lines.append("")

        # Статистика по эффективности
        lines.append("=" * 60)
        lines.append("📊 АНАЛИЗ ЭФФЕКТИВНОСТИ:")
        lines.append("")

        if accounts_with_invites > 0:
            avg_per_active = total_invites / accounts_with_invites
            lines.append(f"📈 Среднее инвайтов на активный аккаунт: {avg_per_active:.1f}")

            # Распределение по группам
            groups = {
                "Супер активные (50+ инвайтов)": 0,
                "Активные (10-49 инвайтов)": 0,
                "Умеренные (1-9 инвайтов)": 0,
                "Неактивные (0 инвайтов)": 0
            }

            for accounts in report_data.values():
                for _, count in accounts:
                    if count >= 50:
                        groups["Супер активные (50+ инвайтов)"] += 1
                    elif count >= 10:
                        groups["Активные (10-49 инвайтов)"] += 1
                    elif count >= 1:
                        groups["Умеренные (1-9 инвайтов)"] += 1
                    else:
                        groups["Неактивные (0 инвайтов)"] += 1

            lines.append("")
            lines.append("👥 РАСПРЕДЕЛЕНИЕ АККАУНТОВ:")
            for group_name, count in groups.items():
                if total_accounts > 0:
                    percentage = (count / total_accounts) * 100
                    lines.append(f"   {group_name}: {count} ({percentage:.1f}%)")

        lines.append("")
        lines.append("=" * 60)
        lines.append("🤖 Отчет сгенерирован автоматически")

        return '\n'.join(lines)

    def get_summary_stats(self) -> Dict:
        """Возвращает краткую статистику для уведомлений"""
        try:
            report_data = self.scan_all_accounts()

            total_accounts = sum(len(accounts) for accounts in report_data.values())
            total_invites = sum(sum(count for _, count in accounts) for accounts in report_data.values())
            accounts_with_invites = sum(
                sum(1 for _, count in accounts if count > 0) for accounts in report_data.values())

            # Находим топ аккаунт
            all_accounts = []
            for accounts in report_data.values():
                all_accounts.extend(accounts)

            top_account = max(all_accounts, key=lambda x: x[1]) if all_accounts else ("", 0)

            return {
                'total_accounts': total_accounts,
                'total_invites': total_invites,
                'accounts_with_invites': accounts_with_invites,
                'top_account_name': top_account[0],
                'top_account_invites': top_account[1],
                'folders_scanned': len([f for f, accounts in report_data.items() if accounts])
            }

        except Exception as e:
            logger.error(f"❌ Ошибка получения статистики: {e}")
            return {
                'total_accounts': 0,
                'total_invites': 0,
                'accounts_with_invites': 0,
                'top_account_name': '',
                'top_account_invites': 0,
                'folders_scanned': 0
            }