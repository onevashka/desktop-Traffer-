from loguru import logger
import sys

# ------------------------------------------------------------
# Флаг режима работы:
#   True  — развёрнутое DEBUG-логирование и в консоль, и в файл
#   False — только INFO+ в оба места
DEBUG_MODE = False
# ------------------------------------------------------------

# Убираем все предустановленные хендлеры
logger.remove()

# Вычисляем динамические уровни
file_level    = "DEBUG" if DEBUG_MODE else "INFO"
console_level = "DEBUG" if DEBUG_MODE else "INFO"

# Хендлер для файла — mode="w" гарантирует, что при старте
# файл очищается и туда попадут только новые записи не ниже file_level
logger.add(
    "logs/factory.log",
    mode="w",
    level=file_level,
    rotation="1 MB",
    retention="7 days",
    encoding="utf-8",
    format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>",
)

# Хендлер для консоли
logger.add(
    sys.stdout,
    level=console_level,
    format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>",
)
