import unittest

from judgescore.reports import build_report


class TestLeaderboard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_leaderboard(self):
        self.assertEqual(self.report["leaderboard"], {"atlas-7b": 0.679, "borealis-13b": 0.681, "cirrus-70b": 0.776})

    def test_categories(self):
        self.assertEqual(self.report["categories"], {
            "coding": {"n": 6, "mean": 0.669},
            "reasoning": {"n": 5, "mean": 0.783},
            "safety": {"n": 4, "mean": 0.75},
            "summarization": {"n": 3, "mean": 0.656},
        })


if __name__ == "__main__":
    unittest.main()
