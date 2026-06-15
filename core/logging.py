import logging
import os
import sys
import structlog

from config import settings

def configure_logging() -> None:
    os.makedirs(settings.LOG_DIR, exist_ok=True)

    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    handlers:list = [logging.StreamHandler(sys.stdout)]

    if not settings.is_development:
        log_file = os.path.join(settings.LOG_DIR, "veritas_ai.log")
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))

        logging.basicConfig(
            format="%(message)s",
            level=log_level,
            handlers=handlers
        )

    # Structlog processors
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if settings.is_development:
        structlog.dev.ConsoleRenderer()
    else:
        structlog.processors.JSONRenderer()

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger, #helps to bind above processes data to the logger
        context_class=dict, #where bound values are stored
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
configure_logging()

logger = structlog.get_logger("veritasai") 