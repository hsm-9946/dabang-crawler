from __future__ import annotations

from loguru import logger
from pathlib import Path
import sys

# Ensure project root is on sys.path when running as a script (python app/main.py)
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import settings  # noqa: E402
from app.gui import main as gui_main  # noqa: E402


def setup_logging() -> None:
    Path(settings.paths.logs).mkdir(parents=True, exist_ok=True)
    logger.remove()
    logger.add(sys.stderr, level="INFO")
    logger.add(Path(settings.paths.logs) / "app_{time:YYYYMMDD}.log", encoding="utf-8", rotation="00:00")


def main() -> None:
    setup_logging()
    gui_main()


if __name__ == "__main__":
    main()


