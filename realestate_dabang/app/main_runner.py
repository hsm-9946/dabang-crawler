from __future__ import annotations

import argparse
from loguru import logger

from pathlib import Path
from . import config as cfg
from .config import ensure_dirs
from .core.exporter import save_excel
from .core.filters import apply_filters
from .core.models import CrawlerInput
from .crawler.dabang_crawler import DabangCrawler


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Dabang 크롤러 CLI")
    p.add_argument("--region", required=True, help="지역 키워드")
    p.add_argument("--price-min", type=int, default=0, help="최소 가격(원)")
    p.add_argument("--price-max", type=int, default=None, help="최대 가격(원)")
    p.add_argument("--types", action="append", default=[], help="유형(복수 지정 가능)")
    p.add_argument("--headless", type=lambda s: s.lower() in {"1", "true", "yes"}, default=True)
    p.add_argument("--dedupe", type=lambda s: s.lower() in {"1", "true", "yes"}, default=True)
    p.add_argument("--diagnostics", type=lambda s: s.lower() in {"1", "true", "yes"}, default=False)
    p.add_argument("--output-dir", type=str, default=None, help="Excel 저장 경로 재정의")
    # 분양 관련
    p.add_argument("--sale-building", action="append", default=[], help="분양 건물유형(복수 지정)")
    p.add_argument("--sale-stage", action="append", default=[], help="분양 단계(복수 지정)")
    p.add_argument("--sale-schedule", action="append", default=[], help="분양 일정(복수 지정)")
    p.add_argument("--sale-supply", action="append", default=[], help="공급 유형(복수 지정)")
    return p.parse_args()


def main() -> None:
    ensure_dirs()
    args = parse_args()
    if args.output_dir:
        cfg.OUTPUT_DIR = Path(args.output_dir)
    user_input = CrawlerInput(
        region_keyword=args.region,
        price_min=args.price_min,
        price_max=args.price_max,
        property_types=args.types,
        headless=args.headless,
        dedupe=args.dedupe,
        diagnostics=args.diagnostics,
        sale_building_types=args.sale_building,
        sale_stages=args.sale_stage,
        sale_schedules=args.sale_schedule,
        sale_supply_types=args.sale_supply,
    )
    crawler = DabangCrawler(user_input)
    logger.info("크롤링 시작: {}", user_input.model_dump())
    records, total_cards = crawler.run()
    filtered = apply_filters(records, user_input)
    out = save_excel(filtered, user_input.region_keyword, dedupe=user_input.dedupe)
    logger.success("완료: 카드 {}개 중 {}건 저장 → {}", total_cards, len(filtered), out)


if __name__ == "__main__":
    main()


