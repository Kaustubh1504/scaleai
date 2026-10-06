import unittest

from prefpairs.reports import build_report


class TestDataset(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_training_pairs(self):
        got = [(r["pair_id"], r["chosen"], r["rejected"]) for r in self.report["dataset"]]
        self.assertEqual(got, [
            ("P01", "atlas-7b", "birch-13b"), ("P02", "cobalt-70b", "birch-13b"),
            ("P04", "atlas-7b", "delta-3b"), ("P05", "cobalt-70b", "delta-3b"),
            ("P06", "birch-13b", "delta-3b"), ("P08", "cobalt-70b", "atlas-7b"),
            ("P10", "cobalt-70b", "birch-13b"), ("P11", "atlas-7b", "delta-3b"),
            ("P12", "atlas-7b", "birch-13b"), ("P14", "atlas-7b", "cobalt-70b"),
        ])
        self.assertEqual([r["prompt_id"] for r in self.report["dataset"]][:2], ["pr-101", "pr-102"])

    def test_standings(self):
        self.assertEqual(self.report["standings"], [
            {"model": "atlas-7b", "wins": 5, "losses": 1, "ties": 2, "win_rate": 0.75},
            {"model": "cobalt-70b", "wins": 4, "losses": 1, "ties": 1, "win_rate": 0.75},
            {"model": "birch-13b", "wins": 1, "losses": 4, "ties": 1, "win_rate": 0.25},
            {"model": "delta-3b", "wins": 0, "losses": 4, "ties": 0, "win_rate": 0.0},
        ])


if __name__ == "__main__":
    unittest.main()
