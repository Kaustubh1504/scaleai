import unittest

from skufeed.reports import build_report


class TestSummary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.summary = build_report()["summary"]

    def test_categories(self):
        self.maxDiff = None
        self.assertEqual(self.summary["categories"], {
            "electrical": {"skus": 2, "units": 60, "avg_price": 8.4, "stock_value": 288.0},
            "garden": {"skus": 2, "units": 16, "avg_price": 21.6, "stock_value": 393.0},
            "lighting": {"skus": 2, "units": 10, "avg_price": 29.65, "stock_value": 440.0},
            "paint": {"skus": 1, "units": 20, "avg_price": 38.5, "stock_value": 770.0},
            "safety": {"skus": 2, "units": 37, "avg_price": 9.3, "stock_value": 223.2},
            "tools": {"skus": 3, "units": 37, "avg_price": 430.0, "stock_value": 4398.88},
        })

    def test_top_category(self):
        self.assertEqual(self.summary["top_category"], "tools")

    def test_counts(self):
        self.assertEqual(
            (self.summary["discontinued"], self.summary["duplicates_removed"], self.summary["rejected"]),
            (2, 4, {"bad_date": 2, "bad_price": 2, "bad_qty": 2, "missing_sku": 1, "unknown_category": 3}),
        )


if __name__ == "__main__":
    unittest.main()
