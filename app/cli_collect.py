from __future__ import annotations

import sys
from pathlib import Path
import argparse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import settings
from scraper.dabang_scraper import DabangScraper, ScrapeOptions
from storage.exporter import save_to_excel
import threading


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--region", required=True)
    p.add_argument("--type", default=settings.defaults.property_type, 
                   help="매물 종류: 원룸, 투룸, 오피스텔, 아파트, 주택, 빌라, 전체")
    p.add_argument("--limit", type=int, default=settings.defaults.max_items)
    p.add_argument("--pages", type=int, default=settings.defaults.max_pages)
    # 헤드리스 토글: --headless / --no-headless 둘 다 지원
    p.add_argument("--headless", dest="headless", action="store_true", default=settings.browser.headless)
    p.add_argument("--no-headless", dest="headless", action="store_false")
    p.add_argument("--outdir", default=settings.paths.output)
    args = p.parse_args()

    stop = threading.Event()
    opts = ScrapeOptions(
        region=args.region,
        property_type=args.type,
        price_min=settings.defaults.price_min,
        price_max=settings.defaults.price_max,
        max_items=args.limit,
        max_pages=args.pages,
        headless=args.headless,
    )
    scraper = DabangScraper(opts, stop)
    items = scraper.run()
    out = save_to_excel(items, Path(args.outdir), args.region)
    print(str(out))


if __name__ == "__main__":
    main()


