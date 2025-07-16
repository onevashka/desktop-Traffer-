# debug_sales.py - СОЗДАТЬ НОВЫЙ ФАЙЛ для отладки

from pathlib import Path
from paths import *
import asyncio


def check_sales_folders():
    """Проверяет папки продаж и их содержимое"""

    print("🔍 Отладка загрузки продаж...")
    print("=" * 50)

    # Проверяем маппинг папок из manager.py
    sales_folders = {
        "registration": WORK_ACCOUNTS_SALE_FOLDER,
        "ready_tdata": TDATA_FOLDER,
        "ready_sessions": SESSIONS_JSON_FOLDER,
        "middle": MIDDLE_ACCOUNTS_FOLDER,
        "dead": DEAD_SALES_FOLDER,
        "frozen": FROZEN_SALES_FOLDER,
        "invalid": INVALID_SALES_FORMAT_FOLDER
    }

    print("📁 Проверяем маппинг папок продаж:")
    for status, folder_path in sales_folders.items():
        exists = "✅" if folder_path.exists() else "❌"
        print(f"  {exists} {status}: {folder_path}")

        if folder_path.exists():
            # Ищем .session файлы
            session_files = list(folder_path.glob("*.session"))
            json_files = list(folder_path.glob("*.json"))

            print(f"    📄 .session файлов: {len(session_files)}")
            print(f"    📄 .json файлов: {len(json_files)}")

            # Показываем файлы в папке Регистрация
            if status == "registration" and session_files:
                print(f"    📋 Файлы в папке Регистрация:")
                for session_file in session_files:
                    json_file = session_file.with_suffix(".json")
                    has_json = "✅" if json_file.exists() else "❌"
                    print(f"      {has_json} {session_file.name} -> {json_file.name}")

        print()

    print("=" * 50)

    # Проверяем что в paths.py
    print("📂 Пути из paths.py:")
    print(f"  BASE_PATH: {BASE_PATH}")
    print(f"  WORK_SALES_FOLDER: {WORK_SALES_FOLDER}")
    print(f"  WORK_ACCOUNTS_SALE_FOLDER: {WORK_ACCOUNTS_SALE_FOLDER}")
    print()

    # Проверяем реальную структуру папок
    print("🗂️ Реальная структура папки 'Продажи':")
    sales_base = BASE_PATH / "Продажи"
    if sales_base.exists():
        for item in sales_base.iterdir():
            if item.is_dir():
                session_count = len(list(item.glob("*.session")))
                print(f"  📁 {item.name}: {session_count} .session файлов")
    else:
        print("  ❌ Папка 'Продажи' не существует!")


async def test_manager_loading():
    """Тестирует загрузку через AccountManager"""

    print("\n🧪 Тестируем загрузку через AccountManager...")

    try:
        from src.accounts.manager import AccountManager

        manager = AccountManager()

        # Выводим информацию о папках которые менеджер будет сканировать
        print("\n📋 Папки которые будет сканировать менеджер:")

        print("  🚀 Трафик:")
        for status, folder_path in manager.traffic_folders.items():
            exists = "✅" if folder_path.exists() else "❌"
            print(f"    {exists} {status}: {folder_path}")

        print("  💰 Продажи:")
        for status, folder_path in manager.sales_folders.items():
            exists = "✅" if folder_path.exists() else "❌"
            session_count = len(list(folder_path.glob("*.session"))) if folder_path.exists() else 0
            print(f"    {exists} {status}: {folder_path} ({session_count} файлов)")

        # Запускаем сканирование
        print(f"\n🔄 Запускаем сканирование...")
        await manager.scan_all_folders()

        # Проверяем результаты
        print(f"\n📊 Результаты загрузки:")

        traffic_accounts = [name for name, data in manager.accounts.items() if data.category == "traffic"]
        sales_accounts = [name for name, data in manager.accounts.items() if data.category == "sales"]

        print(f"  🚀 Трафик: {len(traffic_accounts)} аккаунтов")
        if traffic_accounts:
            for name in traffic_accounts[:3]:  # Показываем первые 3
                print(f"    - {name}")

        print(f"  💰 Продажи: {len(sales_accounts)} аккаунтов")
        if sales_accounts:
            for name in sales_accounts:  # Показываем все
                account_data = manager.accounts[name]
                print(f"    - {name} (статус: {account_data.status})")
        else:
            print(f"    ❌ Аккаунты продаж НЕ ЗАГРУЖЕНЫ!")

            # Дополнительная диагностика
            print(f"\n🔍 Дополнительная диагностика:")
            reg_folder = manager.sales_folders["registration"]
            print(f"  Папка регистрации: {reg_folder}")
            print(f"  Существует: {reg_folder.exists()}")

            if reg_folder.exists():
                all_files = list(reg_folder.iterdir())
                session_files = list(reg_folder.glob("*.session"))
                json_files = list(reg_folder.glob("*.json"))

                print(f"  Всего файлов: {len(all_files)}")
                print(f"  .session файлов: {len(session_files)}")
                print(f"  .json файлов: {len(json_files)}")

                if session_files:
                    print(f"  Файлы .session:")
                    for f in session_files:
                        print(f"    - {f.name}")

                if json_files:
                    print(f"  Файлы .json:")
                    for f in json_files:
                        print(f"    - {f.name}")

    except Exception as e:
        print(f"❌ Ошибка тестирования менеджера: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Основная функция отладки"""
    check_sales_folders()
    await test_manager_loading()


if __name__ == "__main__":
    asyncio.run(main())