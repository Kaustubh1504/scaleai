import unittest

from prefrank.reports import build_report


class TestRatings(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_comparisons_used(self):
        self.assertEqual(self.report["comparisons_used"], 18)

    def test_games_played(self):
        games = {mid: row["games"] for mid, row in self.report["models"].items()}
        self.assertEqual(games, {
            "atlas-7b": 10, "borealis-13b": 9, "cirrus-70b": 10, "delta-3b": 3, "ember-8x7b": 4,
        })

    def test_1_win_rates(self):
        rates = {mid: (row["wins"], row["ties"], row["win_rate"]) for mid, row in self.report["models"].items()}
        self.assertEqual(rates, {
            "atlas-7b": (2, 3, 0.35),
            "borealis-13b": (1, 1, 0.167),
            "cirrus-70b": (7, 1, 0.75),
            "delta-3b": (1, 0, 0.333),
            "ember-8x7b": (1, 1, 0.375),
        })

    def test_2_elo_ratings(self):
        elo = {mid: row["elo"] for mid, row in self.report["models"].items()}
        self.assertEqual(elo, {
            "atlas-7b": 969.6,
            "borealis-13b": 949.3,
            "cirrus-70b": 1094.2,
            "delta-3b": 986.1,
            "ember-8x7b": 1000.7,
        })


if __name__ == "__main__":
    unittest.main()
