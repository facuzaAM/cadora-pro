import logging
import sys
from pathlib import Path

from loguru import logger

from app.config import settings


class InterceptHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = str(record.levelno)
        logger.log(level, record.getMessage())


def setup_logging() -> None:
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )

    log_level = "DEBUG" if settings.DEBUG else "INFO"

    logger.remove()

    logger.add(
        sys.stdout,
        format=log_format,
        level=log_level,
        colorize=True,
    )

    if settings.LOG_FILE:
        try:
            log_path = Path(settings.LOG_FILE)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            logger.add(
                str(log_path),
                format=log_format,
                level=log_level,
                rotation="10 MB",
                retention="30 days",
                compression="gz",
            )
        except OSError:
            logger.warning("Could not create log file at {}", settings.LOG_FILE)

    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

    for name in ("uvicorn", "uvicorn.access", "uvicorn.error", "sqlalchemy.engine"):
        logging.getLogger(name).handlers = [InterceptHandler()]
        logging.getLogger(name).propagate = False

    logger.info("Logging configured — level={}", log_level)
