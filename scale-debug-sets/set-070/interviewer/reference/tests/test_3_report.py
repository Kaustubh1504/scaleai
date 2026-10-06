import unittest

from hitlroute.reports import build_report


class TestReport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.summary = build_report()["summary"]

    def test_auto_accept_rate(self):
        self.assertEqual(self.summary["auto_accept_rate"], {"caption": 0.3, "pii": 0.375, "toxicity": 0.3})

    def test_review_load(self):
        self.assertEqual(
            (self.summary["review_load"], self.summary["backlog"]),
            ({"r01": 4, "r02": 3, "r03": 2, "r05": 2, "r06": 2, "r07": 1, "r10": 2}, 3),
        )

    def test_mean_review_confidence(self):
        self.assertEqual(self.summary["mean_review_confidence"], 0.644)


if __name__ == "__main__":
    unittest.main()
