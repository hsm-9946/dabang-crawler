from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class CrawlerInput(BaseModel):
    """크롤러 입력 파라미터."""

    region_keyword: str = Field(..., description="지역 키워드")
    price_min: Optional[int] = Field(None, description="최소 가격(원)")
    price_max: Optional[int] = Field(None, description="최대 가격(원)")
    property_types: List[str] = Field(default_factory=list, description="유형 리스트")
    headless: bool = Field(True, description="헤드리스 모드 on/off")
    dedupe: bool = Field(False, description="중복 제거 여부")
    diagnostics: bool = Field(False, description="진단 모드(0건 시 스냅샷/HTML 저장)")
    # 분양 관련 필터(선택사항)
    sale_building_types: List[str] = Field(default_factory=list, description="분양 건물유형 필터")
    sale_stages: List[str] = Field(default_factory=list, description="분양단계 필터")
    sale_schedules: List[str] = Field(default_factory=list, description="분양일정 필터")
    sale_supply_types: List[str] = Field(default_factory=list, description="공급유형 필터")

    @field_validator("price_min", "price_max")
    @classmethod
    def non_negative(cls, v: Optional[int]) -> Optional[int]:
        if v is None:
            return v
        if v < 0:
            raise ValueError("가격은 0 이상이어야 합니다.")
        return v


class Record(BaseModel):
    """수집 데이터 레코드."""

    lot_address: str
    price: int
    property_type: str
    maintenance_fee: int
    url: str
    source: str = "dabang"
    collected_at: str


