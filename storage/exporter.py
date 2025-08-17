from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Iterable

import pandas as pd

from scraper.dabang_scraper import Item
from config import settings


COLS = [
    "address",
    "price_text",
    "maintenance_fee",
    "realtor",
    "posted_at",
    "property_type",
    "area_m2",
    "floor",
    "url",
    "item_id",
]

# 한국어 컬럼명 매핑(요청된 5개 필수 필드)
CORE_COLS = ["address", "price_text", "maintenance_fee", "realtor", "posted_at"]
KOREAN_COLS_MAP = {
    "address": "주소",
    "price_text": "금액",
    "maintenance_fee": "관리비",
    "realtor": "부동산",
    "posted_at": "올린 날짜/시간",
}


def save_to_excel(items: Iterable[Item], outdir: Path, region: str) -> Path:
    """수집 결과를 엑셀로 저장.

    - 시트 분리: `property_type` 별로 개별 시트 생성(예: 원룸, 투룸, 오피스텔 등)
    - 각 시트는 5개 핵심 컬럼만 한국어 헤더로 저장
    - 기존 시트가 있으면 새 데이터를 추가 (중복 제거 없음)
    - 항상 새로운 시트에 저장
    """
    outdir.mkdir(parents=True, exist_ok=True)
    data = [asdict(i) for i in items]
    df = pd.DataFrame(data, columns=COLS)
    
    # 스키마 보정: 누락 컬럼 추가
    for c in CORE_COLS:
        if c not in df.columns:
            df[c] = None
    
    # 타임스탬프를 포함한 고유 파일명 생성 (중복 방지)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = outdir / f"dabang_{region}_{timestamp}.xlsx"
    
    with pd.ExcelWriter(path, engine="openpyxl") as w:
        if df.empty:
            # 빈 결과면 기본 시트 생성
            pd.DataFrame(columns=[KOREAN_COLS_MAP[c] for c in CORE_COLS]).to_excel(
                w, sheet_name="원룸", index=False
            )
        else:
            # 매물 유형별로 시트 분리하여 저장
            groups = df.groupby(df["property_type"].fillna("기타"))
            
            for ptype, g in groups:
                name = str(ptype).strip() or "기타"
                safe_name = (
                    name.replace("/", "-").replace("\\", "-").replace("*", "｣").replace("[", "(").replace("]", ")")
                )[:31]
                
                # 5개 핵심 컬럼만 한국어 헤더로 저장
                new_df = g[CORE_COLS].rename(columns=KOREAN_COLS_MAP)
                new_df.to_excel(w, sheet_name=safe_name, index=False)
    
    return path


