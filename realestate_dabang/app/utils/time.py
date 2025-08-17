from __future__ import annotations

from datetime import datetime
import re


def now_timestamp_str() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def slugify_for_filename(text: str) -> str:
    s = re.sub(r"\s+", "_", text.strip())
    s = re.sub(r"[^0-9A-Za-z가-힣_\-]+", "", s)
    return s[:60]


