from __future__ import annotations

import logging
from contextvars import ContextVar

from app.config import Settings


REQUEST_ID_CONTEXT: ContextVar[str] = ContextVar("request_id", default="-")
APP_LOGGER_NAME = "oil_gasoline_simulator"
_LOGGING_CONFIGURED = False


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = REQUEST_ID_CONTEXT.get("-")
        return True


def _bind_handlers(
    logger_name: str,
    *,
    handlers: list[logging.Handler],
    level: int,
) -> logging.Logger:
    logger = logging.getLogger(logger_name)
    logger.setLevel(level)
    logger.handlers.clear()
    for handler in handlers:
        logger.addHandler(handler)
    logger.propagate = False
    return logger


def configure_logging(settings: Settings) -> logging.Logger:
    global _LOGGING_CONFIGURED

    logger = logging.getLogger(APP_LOGGER_NAME)
    if _LOGGING_CONFIGURED:
        return logger

    settings.log_dir.mkdir(parents=True, exist_ok=True)

    console_handler = logging.StreamHandler()
    file_handler = logging.FileHandler(
        settings.log_file_path,
        mode="w" if settings.truncate_logs_on_startup else "a",
        encoding="utf-8",
    )

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s req=%(request_id)s %(name)s %(message)s"
    )
    request_filter = RequestIdFilter()

    for handler in (console_handler, file_handler):
        handler.setFormatter(formatter)
        handler.addFilter(request_filter)

    level = getattr(logging, settings.log_level, logging.INFO)
    shared_handlers = [console_handler, file_handler]
    logger = _bind_handlers(APP_LOGGER_NAME, handlers=shared_handlers, level=level)
    _bind_handlers("uvicorn", handlers=shared_handlers, level=level)
    _bind_handlers("uvicorn.error", handlers=shared_handlers, level=level)
    _bind_handlers("uvicorn.access", handlers=shared_handlers, level=level)

    _LOGGING_CONFIGURED = True
    logger.info(
        "logging_configured log_file=%s level=%s truncate_on_startup=%s",
        settings.log_file_path,
        settings.log_level,
        settings.truncate_logs_on_startup,
    )
    return logger


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"{APP_LOGGER_NAME}.{name}")
