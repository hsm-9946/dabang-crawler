from __future__ import annotations

from typing import List
from scraper.dabang_scraper import Item


def dedup_items(items: List[Item]) -> List[Item]:
    """중복 제거 비활성화 - 모든 아이템을 그대로 반환"""
    # 중복 제거하지 않고 모든 아이템을 그대로 반환
    return items


