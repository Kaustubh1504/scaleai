import unittest

from consensus.reports import build_report

EXPECTED = {
    "ann-01": {"accuracy": 1.0, "gold_answered": 2, "blocked": False},
    "ann-02": {"accuracy": 1.0, "gold_answered": 2, "blocked": False},
    "ann-03": {"accuracy": 0.5, "gold_answered": 2, "blocked": False},
    "ann-04": {"accuracy": 0.5, "gold_answered": 2, "blocked": False},
    "ann-05": {"accuracy": 0.0, "gold_answered": 2, "blocked": True},
    "ann-06": {"accuracy": 0.5, "gold_answered": 0, "blocked": False},
    "ann-07": {"accuracy": 1.0, "gold_answered": 2, "blocked": False},
}


class TestAnnotatorQuality(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_only_active_annotators_listed(self):
        self.assertEqual(sorted(self.report["annotators"]), sorted(EXPECTED))

    def test_blocked_annotators(self):
        blocked = sorted(a for a, row in self.report["annotators"].items() if row["blocked"])
        self.assertEqual(blocked, ["ann-05"])

    def test_quality_table(self):
        self.maxDiff = None
        self.assertEqual(self.report["annotators"], EXPECTED)


if __name__ == "__main__":
    unittest.main()
