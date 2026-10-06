import unittest

from nightshift.reports import build_report


class TestSummary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.summary = build_report()["summary"]

    def test_counts(self):
        self.assertEqual(self.summary["counts"], {"succeeded": 8, "dead": 2, "skipped": 2, "pending": 0})

    def test_total_attempts(self):
        self.assertEqual(self.summary["total_attempts"], 13)

    def test_mean_attempts(self):
        self.assertEqual(self.summary["mean_attempts"], 1.3)

    def test_busy_minutes(self):
        self.assertEqual(self.summary["busy_minutes"], 76.7)


if __name__ == "__main__":
    unittest.main()
