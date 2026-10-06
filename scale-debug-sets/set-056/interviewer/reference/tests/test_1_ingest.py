import unittest

from skufeed.reports import build_report


class TestIngest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_rejects(self):
        self.assertEqual([tuple(r) for r in self.report["rejects"]], [
            ("supplier_a", 5, "missing_sku"),
            ("supplier_a", 7, "unknown_category"),
            ("supplier_a", 8, "bad_qty"),
            ("supplier_a", 10, "bad_qty"),
            ("supplier_a", 12, "bad_date"),
            ("supplier_a", 14, "unknown_category"),
            ("supplier_b", 8, "bad_price"),
            ("supplier_b", 9, "bad_date"),
            ("supplier_b", 10, "unknown_category"),
            ("supplier_b", 15, "bad_price"),
        ])

    def test_accepted_per_source(self):
        self.assertEqual(self.report["accepted"], {"supplier_a": 8, "supplier_b": 10})

    def test_every_row_accounted_for(self):
        total = sum(self.report["accepted"].values()) + len(self.report["rejects"])
        self.assertEqual(total, 28)


if __name__ == "__main__":
    unittest.main()
