from __future__ import annotations

import sys
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scraper.dabang_selenium import DabangSelenium, SelOptions
from storage.exporter import save_to_excel


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--region", required=True)
    p.add_argument("--type", default="원룸")
    p.add_argument("--limit", type=int, default=100)
    p.add_argument("--headless", action="store_true", default=True)
    p.add_argument("--outdir", default="output")
    args = p.parse_args()

    opts = SelOptions(region=args.region, property_type=args.type, max_items=args.limit, headless=args.headless)
    rows = DabangSelenium(opts).run()
    out = save_to_excel(rows, Path(args.outdir), args.region)
    print(str(out))


if __name__ == "__main__":
    main()


