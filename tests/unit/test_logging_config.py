"""Unit tests for the logging configuration."""

import logging

import pytest

from finance_engine.logging_config import PACKAGE_LOGGER_NAME, setup_logging


def _real_handlers():
    logger = logging.getLogger(PACKAGE_LOGGER_NAME)
    return [h for h in logger.handlers if not isinstance(h, logging.NullHandler)]


@pytest.fixture(autouse=True)
def cleanup_handlers():
    """Detach and close handlers created by each test."""
    yield
    logger = logging.getLogger(PACKAGE_LOGGER_NAME)
    for handler in _real_handlers():
        handler.close()
        logger.removeHandler(handler)


def test_setup_logging_writes_to_file(tmp_path):
    log_file = tmp_path / "logs" / "test.log"  # parent folder does not exist yet

    setup_logging(level="INFO", log_file=str(log_file))
    logging.getLogger("finance_engine.test").info("hello log")

    assert "hello log" in log_file.read_text(encoding="utf-8")


def test_setup_logging_does_not_duplicate_handlers(tmp_path):
    log_file = str(tmp_path / "test.log")

    setup_logging(log_file=log_file)
    setup_logging(log_file=log_file)

    assert len(_real_handlers()) == 2  # one console + one file