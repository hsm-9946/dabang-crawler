from __future__ import annotations

"""행정안전부 법정동코드 전체자료(.txt) → data/regions_kr.json 변환 스크립트.

입력 포맷 예(탭 구분):
  법정동코드\t법정동명\t폐지여부
  2611051000\t부산광역시 중구 중앙동1가\t존재

사용법:
  python scripts/build_regions_from_mois.py /path/법정동코드_전체자료.txt

출력:
  data/regions_kr.json (시/도 → 시/군/구 → 읍/면/동 구조)
"""

import json
import sys
from collections import defaultdict
from pathlib import Path


def main(src_path: str) -> None:
    path = Path(src_path)
    if not path.exists():
        raise SystemExit(f"file not found: {path}")

    provinces: dict[str, dict] = {}
    cities_by_prov: dict[str, dict[str, dict]] = defaultdict(dict)
    towns_by_city: dict[str, dict[str, dict]] = defaultdict(dict)

    # 인코딩 자동 처리: 우선 UTF-8, 실패 시 CP949
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("cp949", errors="ignore")

    lines = text.splitlines()
    if not lines:
        raise SystemExit("empty file")
    head = lines[0]
    sep = "\t" if "\t" in head else ","
    for line in lines[1:]:  # 헤더 스킵
        parts = [p.strip() for p in line.strip().split(sep)]
        if len(parts) < 3:
            continue
        code, name, active = parts[0], parts[1], parts[2]
        if active and active.startswith("폐지"):
            continue
        # 코드 구성: 시도(2) + 시군구(3) + 읍면동(3) + 리(2)
        if len(code) < 10:
            continue
        sido = code[:2]
        sigungu = code[2:5]
        eupmyeon = code[5:8]
        # 분해된 명칭(시도/시군구/읍면동)
        tokens = name.split()
        if len(tokens) >= 3:
            p_name, c_name, t_name = tokens[0], tokens[1], " ".join(tokens[2:])
        elif len(tokens) == 2:
            p_name, c_name = tokens[0], tokens[1]
            t_name = ""
        else:
            continue

        # 시/도
        provinces.setdefault(sido, {"code": sido, "name": p_name, "children": []})
        # 시/군/구
        city_key = sido + sigungu
        cities = cities_by_prov[sido]
        cities.setdefault(sigungu, {"code": city_key, "name": c_name, "children": []})
        # 읍/면/동 (있을 때만)
        if eupmyeon != "000":
            town_key = city_key + eupmyeon
            towns = towns_by_city[city_key]
            towns.setdefault(eupmyeon, {"code": town_key, "name": t_name or c_name})

    # children 연결
    for city_key, towns in towns_by_city.items():
        # city_key = sido(2)+sigungu(3)
        sido = city_key[:2]
        sigungu = city_key[2:5]
        city = cities_by_prov[sido][sigungu]
        city["children"] = list(towns.values())

    for sido, cities in cities_by_prov.items():
        prov = provinces[sido]
        prov["children"] = list(cities.values())

    out = {"provinces": list(provinces.values())}
    out_path = Path(__file__).resolve().parents[1] / "data" / "regions_kr.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"written: {out_path} (provinces={len(out['provinces'])})")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/build_regions_from_mois.py /path/법정동코드_전체자료.txt")
        raise SystemExit(2)
    main(sys.argv[1])


