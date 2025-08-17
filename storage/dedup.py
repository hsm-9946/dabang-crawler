from __future__ import annotations

from typing import List
from scraper.dabang_scraper import Item


def dedup_items(items: List[Item]) -> List[Item]:
    seen_url: set[str] = set()
    out: List[Item] = []
    seen_combo: set[tuple[str, str]] = set()
    for i in items:
        key_url = i.url or ""
        combo = (i.address, i.price_text)
        if key_url and key_url in seen_url:
            continue
        if combo in seen_combo:
            continue
        if key_url:
            seen_url.add(key_url)
        seen_combo.add(combo)
        out.append(i)
    return out


