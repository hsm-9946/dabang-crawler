from __future__ import annotations

from pathlib import Path

from scraper.dabang_scraper import DabangScraper, ScrapeOptions


def test_e2e_dry_run(tmp_path: Path, monkeypatch):
    # headless로 1페이지, 3건만 시도 (실제 네트워크 의존 → CI에서는 스킵 권장)
    opts = ScrapeOptions(
        region="부산 기장",
        property_type="원룸",
        price_min=0,
        price_max=2000000,
        max_items=3,
        max_pages=1,
        headless=True,
    )
    import threading

    stop = threading.Event()
    s = DabangScraper(opts, stop)
    items = s.run()
    assert isinstance(items, list)


