from __future__ import annotations

from typing import Iterable, List
from loguru import logger

from .models import CrawlerInput, Record


def record_matches_filters(record: Record, user_input: CrawlerInput) -> bool:
    """레코드가 사용자 필터에 부합하는지 확인.

    - 지역 키워드 포함 여부: lot_address에 부분 문자열로 포함되면 통과
    - 가격 범위: price_min/max 범위 내면 통과
    - 유형: property_types가 비어있다면 모든 유형 허용, 아니면 포함될 때만 통과
    """

    region_ok = user_input.region_keyword.strip() in record.lot_address

    price_ok = True
    if user_input.price_min is not None and record.price < user_input.price_min:
        price_ok = False
    if user_input.price_max is not None and record.price > user_input.price_max:
        price_ok = False

    type_ok = (
        True
        if not user_input.property_types
        else any(t in record.property_type for t in user_input.property_types)
    )

    if not (region_ok and price_ok and type_ok):
        logger.debug(
            "필터 미통과: region_ok={}, price_ok={}, type_ok={}, rec={}",
            region_ok,
            price_ok,
            type_ok,
            record.model_dump(),
        )
    return region_ok and price_ok and type_ok


def apply_filters(records: Iterable[Record], user_input: CrawlerInput) -> List[Record]:
    """레코드 리스트에 필터를 적용하여 반환."""

    rec_list = list(records)
    filtered: List[Record] = [r for r in rec_list if record_matches_filters(r, user_input)]
    logger.info("필터 적용: {}건 → {}건", len(rec_list), len(filtered))
    return filtered


