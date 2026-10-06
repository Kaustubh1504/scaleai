import unittest

from fraudlens.reports import build_report


class TestReport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_rejected_rows(self):
        self.assertEqual(self.report["rejected"], [
            {"txn_id": "T015", "reason": "missing:card_id"},
            {"txn_id": "T021", "reason": "missing:amount"},
            {"txn_id": "T024", "reason": "unparseable"},
            {"txn_id": "T027", "reason": "unparseable"},
            {"txn_id": "T029", "reason": "missing:amount"},
        ])

    def test_summary(self):
        self.assertEqual(self.report["summary"], {
            "loaded": 25,
            "rejected": 5,
            "total_usd": 5250.4,
            "blocked": ["T007"],
        })


if __name__ == "__main__":
    unittest.main()
