import unittest

from prefrank.reports import build_report


class TestRatings(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_comparisons_used(self):
        self.assertEqual(self.report["used"], 22)

    def test_win_rates(self):
        self.assertEqual(self.report["win_rates"], {
            "atlas-7b": {"games": 13, "wins": 8, "ties": 1, "win_rate": 0.654},
            "borealis": {"games": 10, "wins": 4, "ties": 0, "win_rate": 0.4},
            "cirrus-2": {"games": 11, "wins": 3, "ties": 1, "win_rate": 0.318},
            "drift-xl": {"games": 10, "wins": 6, "ties": 0, "win_rate": 0.6},
        })

    def test_elo(self):
        self.assertEqual(self.report["elo"],
                         {"atlas-7b": 1030.9, "borealis": 978.7, "cirrus-2": 962.5, "drift-xl": 1028.0})


if __name__ == "__main__":
    unittest.main()
