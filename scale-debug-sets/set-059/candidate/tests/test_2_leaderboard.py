import unittest

from prefrank.reports import build_report


class TestLeaderboard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_leaderboard(self):
        self.assertEqual(self.report["leaderboard"], ["atlas-7b", "drift-xl", "borealis", "cirrus-2"])

    def test_contested_prompts(self):
        self.assertEqual(self.report["contested"], ["p03", "p04", "p06", "p10"])


if __name__ == "__main__":
    unittest.main()
