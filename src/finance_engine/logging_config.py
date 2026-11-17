"""Centralised logging configuration.

``setup_logging`` is meant to be called once, at application start-up (by the
CLI). Library modules only need ``logging.getLogger(__name__)``.
"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

PACKAGE_LOGGER_NAME = "finance_engine"
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


def _remove_existing_handlers(logger: logging.Logger) -> None:
    """Close and detach handlers added by a previous setup (keep NullHandler)."""
    for handler in list(logger.handlers):
        if not isinstance(handler, logging.NullHandler):
            handler.close()
            logger.removeHandler(handler)


def setup_logging(
    level: str = "INFO",
    log_file: str = "logs/finance_engine.log",
    max_bytes: int = 1_000_000,
    backup_count: int = 3,
) -> None:
    """Configure console and rotating-file logging for the whole package.

    Calling this function several times is safe: previous handlers are
    replaced, so messages are never duplicated.

    Args:
        level: Minimum level to record (``"DEBUG"``, ``"INFO"``, ...).
        log_file: Path of the log file. Parent folders are created if needed.
        max_bytes: Size at which the log file is rotated.
        backup_count: Number of rotated files to keep.
    """
    package_logger = logging.getLogger(PACKAGE_LOGGER_NAME)
    _remove_existing_handlers(package_logger)
    package_logger.setLevel(level.upper())

    formatter = logging.Formatter(LOG_FORMAT)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    package_logger.addHandler(console_handler)

    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        log_path, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    package_logger.addHandler(file_handler)