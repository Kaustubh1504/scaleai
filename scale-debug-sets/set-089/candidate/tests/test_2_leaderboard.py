import unittest

from evalboard.report import build_leaderboard


class TestLeaderboard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = build_leaderboard()
        cls.order = [row["team"] for row in cls.result["board"]]

    def test_podium(self):
        self.assertEqual(self.order[:3], ["kelp", "narwhal", "puffin"])
        self.assertEqual([row["rank"] for row in self.result["board"][:3]], [1, 2, 3])

    def test_2_final_standings(self):
        self.assertEqual(self.order,
                         ["kelp", "narwhal", "puffin", "otter", "orca", "lynx", "heron", "wren", "marten"])

    def test_3_benchmark_stats(self):
        self.assertEqual(self.result["benchmarks"], {
            "coding": {"teams": 8, "leader": "puffin", "best": 50.0},
            "latency_ms": {"teams": 7, "leader": "kelp", "best": 200.0},
            "reasoning": {"teams": 8, "leader": "narwhal", "best": 80.0},
            "safety": {"teams": 8, "leader": "otter", "best": 90.0},
        })


if __name__ == "__main__":
    unittest.main()
