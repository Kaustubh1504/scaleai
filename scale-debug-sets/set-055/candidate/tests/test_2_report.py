import unittest

from evalscore.reports import build_report


class TestReport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_weighted_scores(self):
        self.assertEqual(self.report["weighted_scores"],
                         {"alpha": 0.833, "bravo": 0.556, "charlie": 0.556, "delta": 0.167})

    def test_category_accuracy(self):
        self.assertEqual(self.report["category_accuracy"], {
            "alpha": {"code": 0.75, "math": 0.75, "reading": 0.75},
            "bravo": {"code": 0.25, "math": 0.5, "reading": 0.25},
            "charlie": {"code": 0.5, "math": 0.5, "reading": 0.75},
            "delta": {"code": 0.0, "math": 0.5, "reading": 0.0},
        })

    def test_leaderboard(self):
        self.assertEqual(self.report["leaderboard"], ["alpha", "charlie", "bravo", "delta"])


if __name__ == "__main__":
    unittest.main()
