from __future__ import annotations

from pathlib import Path
from loguru import logger

from .config import LOG_DIR, ensure_dirs


def _setup_logging() -> None:
    ensure_dirs()
    logger.remove()
    logger.add(lambda msg: print(msg, end=""))  # 콘솔
    log_path = Path(LOG_DIR) / "dabang_{time:YYYYMMDD}.log"
    logger.add(
        str(log_path),
        rotation="00:00",
        retention="14 days",
        encoding="utf-8",
        enqueue=True,
        level="INFO",
    )


_setup_logging()


