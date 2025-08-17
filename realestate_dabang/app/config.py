from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv


# .env 로드 (옵션)
load_dotenv()


BASE_DIR: Path = Path(__file__).resolve().parents[1]
OUTPUT_DIR: Path = Path(os.getenv("OUTPUT_DIR", BASE_DIR / "output"))
LOG_DIR: Path = Path(os.getenv("LOG_DIR", BASE_DIR / "logs"))
DEBUG_DIR: Path = Path(os.getenv("DEBUG_DIR", BASE_DIR / "debug"))

HEADLESS_DEFAULT: bool = os.getenv("HEADLESS", "true").lower() in {"1", "true", "yes"}
TIMEOUT_SECONDS: int = int(os.getenv("TIMEOUT_SECONDS", "20"))
SCROLL_PAUSE_SECONDS: float = float(os.getenv("SCROLL_PAUSE_SECONDS", "1.2"))

RANDOM_DELAY_MIN: float = float(os.getenv("RANDOM_DELAY_MIN", "0.8"))
RANDOM_DELAY_MAX: float = float(os.getenv("RANDOM_DELAY_MAX", "2.4"))
RETRY_MAX_TRIES: int = int(os.getenv("RETRY_MAX_TRIES", "3"))

USER_AGENT: str = os.getenv(
    "USER_AGENT",
    (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
)

# 설치된 Chrome 메이저 버전을 강제로 지정하고 싶을 때 사용 (예: 138)
CHROME_VERSION_MAIN = os.getenv("CHROME_VERSION_MAIN")
if CHROME_VERSION_MAIN is not None:
    try:
        CHROME_VERSION_MAIN = int(CHROME_VERSION_MAIN)
    except Exception:
        CHROME_VERSION_MAIN = None


def ensure_dirs() -> None:
    """필요한 출력/로그 디렉터리 생성."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    DEBUG_DIR.mkdir(parents=True, exist_ok=True)


