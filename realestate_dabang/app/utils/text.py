from __future__ import annotations

import re
from typing import Optional
from loguru import logger


WHITESPACE_RE = re.compile(r"\s+", re.UNICODE)
EMOJI_RE = re.compile(
    r"[\U00010000-\U0010ffff]",  # surrogate pairs range
    flags=re.UNICODE,
)


def normalize_whitespace(text: str) -> str:
    return WHITESPACE_RE.sub(" ", text).strip()


def strip_emojis(text: str) -> str:
    return EMOJI_RE.sub("", text)


PRICE_NUMBER_RE = re.compile(r"([0-9]+)(?:\s*[,.]?[0-9]*)?")


def _to_int_or_zero(s: str) -> int:
    try:
        return int(s)
    except Exception:
        return 0


def parse_price_to_won(text: str) -> int:
    """한국형 금액 문자열을 원화 정수로 변환.

    지원 예시:
    - "200만원" → 2,000,000
    - "45만" → 450,000
    - "150,000원" → 150,000
    - "보증금 500/월세 50만" → 500000 / 500000 → 월세 500000 반환(우선 순위: 월세 표현 포함 시 월세)
    """

    s = normalize_whitespace(strip_emojis(text))
    if not s:
        return 0

    # 월세/관리비 등 포맷에서 우선 월세/관리비를 파악
    # 월세, 관리비가 같이 있는 경우를 대비하여 먼저 '월세' 또는 '관리비' 뒤의 금액을 잡는다.
    for keyword in ["월세", "관리비"]:
        if keyword in s:
            tail = s.split(keyword, 1)[1]
            amount = _parse_single_amount(tail)
            if amount:
                return amount

    # 일반 금액 파싱
    return _parse_single_amount(s)


def _parse_single_amount(s: str) -> int:
    s = s.replace(",", "")
    match = PRICE_NUMBER_RE.search(s)
    if not match:
        return 0

    num = _to_int_or_zero(match.group(1))
    if "만원" in s or "만" in s:
        return num * 10000
    if "천원" in s or "천" in s:
        return num * 1000
    if "원" in s:
        return num
    # 단위 미포함 시 원 단위로 해석
    return num


# 지번 주소 패턴: 동/읍/면/리 + 공백 + 숫자(-숫자) 형태를 우선 추출
LOT_ADDR_RE = re.compile(r"([가-힣]+(?:동|읍|면|리)\s*\d+(?:-\d+)?)")


def extract_lot_address(text: str) -> Optional[str]:
    s = normalize_whitespace(strip_emojis(text))
    if not s:
        return None
    m = LOT_ADDR_RE.search(s)
    if m:
        return m.group(1)
    # 보조: 구/로/가 포함 케이스 일부 허용
    alt = re.search(r"([가-힣]+(?:가|로|길)\s*\d+(?:-\d+)?)", s)
    if alt:
        return alt.group(1)
    logger.debug("지번 추출 실패: {}", text)
    return None


def parse_maintenance_fee_to_won(text: str) -> int:
    return parse_price_to_won(text)


