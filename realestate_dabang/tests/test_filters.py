from __future__ import annotations

import unittest
from datetime import datetime

from realestate_dabang.app.core.filters import record_matches_filters
from realestate_dabang.app.core.models import CrawlerInput, Record


def make_record(addr: str, price: int, typ: str) -> Record:
    return Record(
        lot_address=addr,
        price=price,
        property_type=typ,
        maintenance_fee=0,
        url="",
        collected_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )


class TestFilters(unittest.TestCase):
    def test_filters(self):
        user_input = CrawlerInput(
            region_keyword="부산 기장",
            price_min=0,
            price_max=2_000_000,
            property_types=["원룸"],
        )
        rec1 = make_record("부산 기장 대변리 123-4", 1_000_000, "원룸")
        rec2 = make_record("부산 해운대 우동 10", 3_000_000, "투룸")
        self.assertTrue(record_matches_filters(rec1, user_input))
        self.assertFalse(record_matches_filters(rec2, user_input))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()


