import logging
import os
import sys
from config import settings

def configure_logging() -> None:
    os.makedirs(settings.LOG_DIR, exist_ok=True)

    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    handlers:list = [logging.StreamHandler(sys.stdout)]

    if not settings.is_development:
        log_file = os.path.join(settings.LOG_DIR, "veritas_ai.log")
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))