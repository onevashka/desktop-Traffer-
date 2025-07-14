# TeleCRM/log_config.py
from loguru import logger
import sys

# Убираем стандартный обработчик
logger.remove()

# Сохраняем в файл
logger.add("logs/factory.log", rotation="1 MB", retention="7 days", encoding="utf-8")

# Будем добавлять динамический handler для виджета, но определим шаблон здесь
LOG_FORMAT = "<green>{time:HH:mm:ss}</green> | <level>{message}</level>"
# На консоль stdout (при запуске из терминала, если нужно)
logger.add(sys.stdout, level="DEBUG", format=LOG_FORMAT)
