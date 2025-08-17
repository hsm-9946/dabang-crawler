from __future__ import annotations

import unittest

from realestate_dabang.app.utils.text import (
    extract_lot_address,
    parse_maintenance_fee_to_won,
    parse_price_to_won,
)


class TestTextParse(unittest.TestCase):
    def test_price_parsing(self):
        self.assertEqual(parse_price_to_won("200만원"), 200 * 10000)
        self.assertEqual(parse_price_to_won("45만"), 45 * 10000)
        self.assertEqual(parse_price_to_won("150,000원"), 150000)
        self.assertEqual(parse_price_to_won("보증금 500/월세 50만"), 50 * 10000)
        self.assertEqual(parse_price_to_won("월세 80만 / 관리비 5만"), 80 * 10000)

    def test_maintenance_parsing(self):
        self.assertEqual(parse_maintenance_fee_to_won("관리비 5만"), 5 * 10000)
        self.assertEqual(parse_maintenance_fee_to_won("관리비 없음"), 0)

    def test_lot_address(self):
        self.assertEqual(extract_lot_address("부산시 기장군 기장읍 대변리 123-4"), "대변리 123-4")
        self.assertIsNotNone(extract_lot_address("해운대구 우동 123"))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()


