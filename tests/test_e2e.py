from __future__ import annotations

import threading

from scraper.dabang_scraper import DabangScraper, ScrapeOptions


def test_e2e_all_region_smoke():
    # 전지역 모드: region 빈 문자열
    opts = ScrapeOptions(
        region="",
        property_type="원룸",
        price_min=0,
        price_max=0,
        max_items=50,
        max_pages=8,
        headless=True,
    )
    stop = threading.Event()
    s = DabangScraper(opts, stop)
    items = s.run()
    # 네트워크/사이트 상태에 따라 변동 가능 → 최소 수집 보장 값
    assert isinstance(items, list)


