"""
Logging configuration for the application.
Uses structured logging with consistent formatting.
"""
import logging
import sys
from app.core.config import settings


def setup_logging() -> None:
    """Configure application-wide logging."""
    log_level = logging.DEBUG if settings.DEBUG else logging.INFO

    log_format = (
        "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s"
    )
    date_format = "%Y-%m-%d %H:%M:%S"

    # Root logger
    logging.basicConfig(
        level=log_level,
        format=log_format,
        datefmt=date_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
    )

    # Silence noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

    logger = logging.getLogger(__name__)
    logger.info(
        "Logging initialised | env=%s | debug=%s",
        settings.ENVIRONMENT,
        settings.DEBUG,
    )


def get_logger(name: str) -> logging.Logger:
    """Return a named logger."""
    return logging.getLogger(name)
