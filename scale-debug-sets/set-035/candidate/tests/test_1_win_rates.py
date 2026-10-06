import unittest

from prefrank.reports import build_report


class TestWinRates(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_excluded_comparisons(self):
        self.assertEqual(self.report["excluded"], {"invalid": 2, "rater": 3, "skipped": 2})

    def test_games_per_model(self):
        self.assertEqual(self.report["games"],
                         {"m-alpha": 12, "m-beta": 13, "m-delta": 12, "m-eps": 10, "m-gamma": 11})

    def test_win_rates(self):
        self.assertEqual(self.report["win_rates"],
                         {"m-alpha": 0.875, "m-beta": 0.692, "m-delta": 0.125, "m-eps": 0.25, "m-gamma": 0.5})


if __name__ == "__main__":
    unittest.main()
