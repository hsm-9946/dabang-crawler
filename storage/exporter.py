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
    - 기존 시트가 있으면 업데이트, 없으면 새로 생성
    """
    outdir.mkdir(parents=True, exist_ok=True)
    data = [asdict(i) for i in items]
    df = pd.DataFrame(data, columns=COLS)
    
    # 스키마 보정: 누락 컬럼 추가
    for c in CORE_COLS:
        if c not in df.columns:
            df[c] = None
    
    # 고정 파일명 사용 (종류별로 하나씩만 시트 생성)
    path = outdir / f"dabang_{region}.xlsx"
    existing: dict[str, pd.DataFrame] = {}
    
    # 기존 파일이 있으면 읽어오기
    if path.exists():
        try:
            existing = pd.read_excel(path, sheet_name=None)  # type: ignore[assignment]
        except Exception:
            existing = {}
    
    with pd.ExcelWriter(path, engine="openpyxl") as w:
        if df.empty and not existing:
            # 빈 결과이고 기존 파일도 없으면 기본 시트 생성
            pd.DataFrame(columns=[KOREAN_COLS_MAP[c] for c in CORE_COLS]).to_excel(
                w, sheet_name="원룸", index=False
            )
        else:
            # 기존 시트들 먼저 기록
            for sheet_name, e_df in existing.items():
                e_df.to_excel(w, sheet_name=sheet_name, index=False)
            
            # 새 데이터가 있으면 처리
            if not df.empty:
                groups = df.groupby(df["property_type"].fillna("기타"))
                
                for ptype, g in groups:
                    name = str(ptype).strip() or "기타"
                    safe_name = (
                        name.replace("/", "-").replace("\\", "-").replace("*", "｣").replace("[", "(").replace("]", ")")
                    )[:31]
                    
                    new_df = g[CORE_COLS].rename(columns=KOREAN_COLS_MAP)
                    old_df = existing.get(safe_name)
                    
                    if old_df is not None and not old_df.empty:
                        # 기존 시트가 있으면 병합하고 중복 제거
                        merged = pd.concat([old_df, new_df], ignore_index=True)
                        merged = merged.drop_duplicates(subset=list(new_df.columns), keep="first")
                        merged.to_excel(w, sheet_name=safe_name, index=False)
                    else:
                        # 기존 시트가 없으면 새로 생성
                        new_df.to_excel(w, sheet_name=safe_name, index=False)
    
    return path


