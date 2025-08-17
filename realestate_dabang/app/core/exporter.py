from __future__ import annotations

from pathlib import Path
from typing import Iterable, List

import pandas as pd
from loguru import logger

from .. import config
from ..utils.time import now_timestamp_str, slugify_for_filename
from .models import Record


COLUMNS_ORDER: List[str] = [
    "lot_address",
    "price",
    "property_type",
    "maintenance_fee",
    "url",
    "source",
    "collected_at",
]


def deduplicate_records(records: List[Record]) -> List[Record]:
    """URL 기준 1차, (lot_address+price) 기준 2차 중복 제거."""

    seen_urls: set[str] = set()
    unique_by_url: List[Record] = []
    for r in records:
        if r.url and r.url not in seen_urls:
            seen_urls.add(r.url)
            unique_by_url.append(r)

    seen_combo: set[tuple[str, int]] = set()
    final: List[Record] = []
    for r in unique_by_url:
        combo = (r.lot_address, r.price)
        if combo not in seen_combo:
            seen_combo.add(combo)
            final.append(r)

    logger.info("중복 제거: {}건 → {}건", len(records), len(final))
    return final


def records_to_dataframe(records: Iterable[Record]) -> pd.DataFrame:
    data = [r.model_dump() for r in records]
    df = pd.DataFrame(data, columns=COLUMNS_ORDER)
    return df


def build_output_path(region_keyword: str) -> Path:
    timestamp = now_timestamp_str()
    region_slug = slugify_for_filename(region_keyword)
    filename = f"dabang_{region_slug}_{timestamp}.xlsx"
    return config.OUTPUT_DIR / filename


def save_excel(records: List[Record], region_keyword: str, dedupe: bool = True) -> Path:
    # 중복 제거 비활성화 - 모든 레코드를 그대로 사용
    logger.info("중복 제거 비활성화: {}건 모두 유지", len(records))
    df = records_to_dataframe(records)
    output_path = build_output_path(region_keyword)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="dabang", index=False)
    logger.success("엑셀 저장 완료: {} ({}건)", str(output_path), len(df))
    return output_path


