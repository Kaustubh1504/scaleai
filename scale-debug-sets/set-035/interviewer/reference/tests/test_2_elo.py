import unittest

from prefrank.reports import build_report


class TestElo(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_elo_ratings(self):
        self.assertEqual(self.report["elo"], {
            "m-alpha": 1118.7, "m-beta": 1062.0, "m-delta": 883.1, "m-eps": 935.8, "m-gamma": 1000.4,
        })

    def test_ratings_are_zero_sum(self):
        self.assertAlmostEqual(sum(self.report["elo"].values()), 5000.0, places=0)

    def test_leaderboard(self):
        self.assertEqual(self.report["leaderboard"], ["m-alpha", "m-beta", "m-gamma", "m-delta"])


if __name__ == "__main__":
    unittest.main()
