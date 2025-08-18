# log_config.py - ЦВЕТНАЯ ВЕРСИЯ БЕЗ DEBUG

from loguru import logger
import sys

# ============================
# ГЛАВНЫЙ ПЕРЕКЛЮЧАТЕЛЬ DEBUG
# ============================
DEBUG_MODE = False
# ============================

# Удаляем все стандартные обработчики
logger.remove()

# Простой и эффективный фильтр
def simple_filter(record):
    """Простой фильтр - блокируем DEBUG если режим выключен"""
    if not DEBUG_MODE and record["level"].name == "DEBUG":
        return False
    return True

# Добавляем обработчики с фильтром
if DEBUG_MODE:
    # В DEBUG режиме - все логи с цветами
    logger.add(
        "logs/factory.log",
        mode="w",
        level="DEBUG",
        rotation="1 MB",
        retention="7 days",
        encoding="utf-8",
        format="<green>{time:HH:mm:ss}</green> | <level>{level:8}</level> | <level>{message}</level>",
        colorize=True
    )

    logger.add(
        sys.stdout,
        level="DEBUG",
        format="<green>{time:HH:mm:ss}</green> | <level>{level:8}</level> | <level>{message}</level>",
        colorize=True
    )
else:
    # В PRODUCTION режиме - только INFO и выше + фильтр + ЦВЕТА
    logger.add(
        "logs/factory.log",
        mode="w",
        level="INFO",
        filter=simple_filter,
        rotation="1 MB",
        retention="7 days",
        encoding="utf-8",
        format="<green>{time:HH:mm:ss}</green> | <level>{level:8}</level> | <level>{message}</level>",
        colorize=True
    )

    logger.add(
        sys.stdout,
        level="INFO",
        filter=simple_filter,
        format="<green>{time:HH:mm:ss}</green> | <level>{level:8}</level> | <level>{message}</level>",
        colorize=True
    )

# РАДИКАЛЬНОЕ решение - если DEBUG_MODE = False, заменяем logger.debug на пустышку
if not DEBUG_MODE:
    def empty_debug(*args, **kwargs):
        pass

    logger.debug = empty_debug

# Логируем состояние системы с цветами
logger.info(f"🔧 Система логирования: DEBUG_MODE = {DEBUG_MODE}")

if not DEBUG_MODE:
    logger.info("🔇 DEBUG логи полностью отключены")
    # Эта строка НЕ должна появиться если все работает правильно:
    logger.debug("❌ ТЕСТ: Этот DEBUG лог НЕ должен быть виден!")
else:
    logger.debug("🔍 DEBUG режим активен")