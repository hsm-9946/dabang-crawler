from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Optional


def normalize_price_text(text: str) -> str:
    """원문 가격 문자열을 최대한 보존하되 불필요 공백만 정리."""
    return (text or "").strip()


def normalize_maintenance_fee(text: str) -> Optional[int]:
    """관리비 금액(원)을 정수로 추출. 없으면 None.

    허용 예시:
    - "관리비 5만" -> 50000
    - "관리비 150,000원" -> 150000
    - "없음" -> None
    """
    s = (text or "").replace(",", "").strip()
    if not s or "없" in s:
        return None
    m = re.search(r"(\d+)(?:\s*(만|천)?)(?:원)?", s)
    if not m:
        return None
    num = int(m.group(1))
    unit = m.group(2)
    if unit == "만":
        return num * 10000
    if unit == "천":
        return num * 1000
    return num


REL_TIME_RE = re.compile(r"(\d+)\s*(분|시간|일)\s*전")
ABS_DATE_RE = re.compile(r"(20\d{2})[./-](\d{1,2})[./-](\d{1,2})")


def to_absolute_time(rel_text: str) -> Optional[str]:
    m = REL_TIME_RE.search(rel_text or "")
    if not m:
        # 절대 날짜가 들어온 경우 YYYY-MM-DD로 정규화
        m2 = ABS_DATE_RE.search(rel_text or "")
        if m2:
            y, mo, d = m2.groups()
            return f"{int(y):04d}-{int(mo):02d}-{int(d):02d} 00:00:00"
        return None
    num = int(m.group(1))
    unit = m.group(2)
    delta = None
    if unit == "분":
        delta = timedelta(minutes=num)
    elif unit == "시간":
        delta = timedelta(hours=num)
    elif unit == "일":
        delta = timedelta(days=num)
    if not delta:
        return None
    dt = datetime.now() - delta
    return dt.strftime("%Y-%m-%d %H:%M:%S")


AREA_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:㎡|m²|m2)")
FLOOR_RE = re.compile(r"(지하\d+층|옥탑|반지하|저층|중층|고층|\d+층)")


def extract_area_m2(text: str) -> Optional[float]:
    m = AREA_RE.search(text or "")
    return float(m.group(1)) if m else None


def extract_floor(text: str) -> Optional[str]:
    m = FLOOR_RE.search(text or "")
    return m.group(1) if m else None


# 주소/지번/행정주소 추출(지번/도로명 우선, 실패 시 행정주소 허용)
LOT_ADDR_RE = re.compile(r"([가-힣]+(?:동|읍|면|리)\s*\d+(?:-\d+)?)")
ROAD_ADDR_RE = re.compile(r"([가-힣]+(?:로|길)\s*\d+(?:-\d+)?)")
# 예: 부산광역시 기장군 기장읍 청강리 278-18, 서울특별시 종로구 청운동 등
# '동/읍/면/리' 세그먼트가 1회 이상 반복될 수 있도록 개선
ADMIN_ADDR_RE = re.compile(
    r"((?:[가-힣]{2,}(?:특별|광역)?시|[가-힣]{2,}도)\s*[가-힣]+(?:시|군|구)(?:\s*[가-힣]+(?:동|읍|면|리))+(?:\s*\d+(?:-\d+)?)?)"
)


def extract_address(text: str) -> Optional[str]:
    s = (text or "").strip()
    m = LOT_ADDR_RE.search(s)
    if m:
        return m.group(1)
    m2 = ROAD_ADDR_RE.search(s)
    if m2:
        return m2.group(1)
    m3 = ADMIN_ADDR_RE.search(s)
    if m3:
        return m3.group(1)
    return None


# 가격 텍스트 추출: 전세/월세/매매 한 문구 또는 숫자+단위 라인
PRICE_TEXT_RE = re.compile(
    r"((전세|월세|매매)\s*[0-9억만원/\s,]+|\d{1,3}(?:,\d{3})*(?:원)?\s*(?:/\s*\d{1,3}(?:,\d{3})*)?)"
)


def extract_price_text(text: str) -> Optional[str]:
    s = (text or "").replace("\n", " ")
    m = PRICE_TEXT_RE.search(s)
    return m.group(1).strip() if m else None


def to_ymd(dt_str: str) -> str:
    # "YYYY-MM-DD HH:MM:SS" 또는 기타 형식에서 날짜 부분만 반환
    m = ABS_DATE_RE.search(dt_str or "")
    if m:
        y, mo, d = m.groups()
        return f"{int(y):04d}-{int(mo):02d}-{int(d):02d}"
    try:
        return datetime.fromisoformat((dt_str or "").strip()).strftime("%Y-%m-%d")
    except Exception:
        return datetime.now().strftime("%Y-%m-%d")


# 공인중개사/부동산명 추출
REALTOR_RE = re.compile(r"([가-힣A-Za-z0-9·\s]{2,}?(?:공인중개사사무소|부동산))")


def extract_realtor(text: str) -> Optional[str]:
    s = (text or "").strip()
    m = REALTOR_RE.search(s)
    return m.group(1).strip() if m else None


