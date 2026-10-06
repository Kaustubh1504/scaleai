import unittest

from prefrank.reports import build_report


class TestLeaderboard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_unplayed_models_not_reported(self):
        self.assertNotIn("fjord-1b", self.report["models"])
        self.assertNotIn("zephyr-1b", self.report["models"])

    def test_annotator_activity(self):
        self.assertEqual(self.report["annotators"], {"ann_kim": 6, "ann_lee": 6, "ann_raj": 6})

    def test_3_leaderboard(self):
        self.assertEqual(self.report["leaderboard"], ["cirrus-70b", "ember-8x7b", "atlas-7b", "borealis-13b"])


if __name__ == "__main__":
    unittest.main()
