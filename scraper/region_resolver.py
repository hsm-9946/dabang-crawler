from __future__ import annotations

from typing import Dict, Tuple


def to_query(sel: Dict, lock_town: bool = False) -> Tuple[str, str | None]:
    parts = []
    if sel.get("province", ("", ""))[1]:
        parts.append(sel["province"][1])
    if sel.get("city", ("", ""))[1]:
        parts.append(sel["city"][1])
    q1 = " ".join(parts)
    q2 = None
    town_name = sel.get("town", ("", ""))[1]
    if town_name:
        q2 = (q1 + " " + town_name).strip()
    if lock_town and q2:
        return q2, None
    return q1, q2


