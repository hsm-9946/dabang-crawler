from __future__ import annotations

import unittest
from datetime import datetime

from realestate_dabang.app.core.exporter import deduplicate_records, records_to_dataframe
from realestate_dabang.app.core.models import Record


def make_record(addr: str, price: int, url: str) -> Record:
    return Record(
        lot_address=addr,
        price=price,
        property_type="원룸",
        maintenance_fee=0,
        url=url,
        collected_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )


class TestExporter(unittest.TestCase):
    def test_deduplicate(self):
        r1 = make_record("A 1", 100, "http://x/1")
        r2 = make_record("A 1", 100, "http://x/1")  # url 중복
        r3 = make_record("A 1", 100, "http://x/3")  # 주소+가격 중복
        out = deduplicate_records([r1, r2, r3])
        self.assertEqual(len(out), 1)

    def test_dataframe_columns(self):
        r1 = make_record("A 1", 100, "http://x/1")
        df = records_to_dataframe([r1])
        self.assertListEqual(
            list(df.columns),
            [
                "lot_address",
                "price",
                "property_type",
                "maintenance_fee",
                "url",
                "source",
                "collected_at",
            ],
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()


