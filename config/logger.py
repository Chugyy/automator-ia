# app/logger.py
import logging
from logging.handlers import RotatingFileHandler
from config.config import settings

LOG_FORMAT = "%(asctime)s — %(name)s — %(levelname)s — %(message)s"
LOG_LEVEL = logging.DEBUG if settings.debug else logging.INFO
LOG_FILE = "app.log"

formatter = logging.Formatter(LOG_FORMAT)

handler = RotatingFileHandler(LOG_FILE, maxBytes=10*1024*1024, backupCount=5)
handler.setFormatter(formatter)

# Add console handler for immediate debugging
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)

logger = logging.getLogger(settings.app_name)
logger.setLevel(LOG_LEVEL)
logger.addHandler(handler)
logger.addHandler(console_handler)