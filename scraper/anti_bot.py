from __future__ import annotations

import random
import time
from typing import Dict


UAS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123 Safari/537.36",
]


def build_context_kwargs() -> Dict:
    return {
        "user_agent": random.choice(UAS),
        "locale": "ko-KR",
        "viewport": {"width": 1440, "height": 900},
        "extra_http_headers": {"Accept-Language": "ko-KR,ko;q=0.9"},
    }


def human_sleep(min_s: float = 0.8, max_s: float = 2.4) -> None:
    time.sleep(random.uniform(min_s, max_s))


def infinite_scroll(page, max_scrolls: int = 50, stop_flag=None) -> None:
    last_height = 0
    stable = 0
    for i in range(max_scrolls):
        if stop_flag and stop_flag.is_set():
            break
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(random.uniform(0.8, 1.6))
        height = page.evaluate("document.body.scrollHeight")
        if height == last_height:
            stable += 1
        else:
            stable = 0
        last_height = height
        if stable >= 3:
            break


def scroll_container(page, container_selector: str, max_scrolls: int = 50, stop_flag=None) -> bool:
    """주어진 스크롤 컨테이너를 내부적으로 스크롤.

    반환: 컨테이너를 찾았는지 여부
    """
    container = page.locator(container_selector).first
    try:
        if container.count() == 0:
            return False
    except Exception:
        return False

    last_height = 0
    stable = 0
    for _ in range(max_scrolls):
        if stop_flag and stop_flag.is_set():
            break
        page.evaluate("el => el.scrollTop = el.scrollHeight", container)
        time.sleep(random.uniform(0.8, 1.6))
        height = page.evaluate("el => el.scrollHeight", container)
        if height == last_height:
            stable += 1
        else:
            stable = 0
        last_height = height
        if stable >= 3:
            break
    return True


