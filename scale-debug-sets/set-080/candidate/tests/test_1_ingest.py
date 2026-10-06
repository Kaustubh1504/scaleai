import unittest

from rosterflow.reports import build_report


class TestIngest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_source_counts(self):
        self.assertEqual(self.report["sources"], {
            "vendor_a": {"rows": 11, "accepted": 6, "rejected": 3, "inactive": 2},
            "vendor_b": {"rows": 11, "accepted": 8, "rejected": 3, "inactive": 0},
            "vendor_c": {"rows": 10, "accepted": 7, "rejected": 2, "inactive": 1},
        })

    def test_rejected_rows(self):
        self.maxDiff = None
        self.assertEqual([(r["source"], r["row"], r["reason"]) for r in self.report["rejected"]], [
            ("vendor_a", 9, "missing email"),
            ("vendor_a", 10, "invalid hours"),
            ("vendor_a", 11, "invalid hours"),
            ("vendor_b", 4, "invalid email"),
            ("vendor_b", 5, "invalid hours"),
            ("vendor_b", 8, "unparseable date"),
            ("vendor_c", 3, "missing email"),
            ("vendor_c", 4, "unparseable date"),
        ])


if __name__ == "__main__":
    unittest.main()
