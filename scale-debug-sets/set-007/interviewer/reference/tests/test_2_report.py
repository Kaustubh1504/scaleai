import unittest

from evalscore.reports import build_report


class TestReport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_weighted_accuracy(self):
        got = {m: s["accuracy"] for m, s in self.report["models"].items()}
        self.assertEqual(got, {"atlas-7b": 0.7, "borealis-13b": 0.7, "cirrus-3b": 0.5})

    def test_parse_failures_and_latency(self):
        got = {m: (s["parse_failures"], s["mean_latency_ms"]) for m, s in self.report["models"].items()}
        self.assertEqual(got, {"atlas-7b": (1, 900.8), "borealis-13b": (1, 850.0), "cirrus-3b": (1, 402.5)})

    def test_by_category(self):
        got = {m: s["by_category"] for m, s in self.report["models"].items()}
        self.assertEqual(got, {
            "atlas-7b": {"logic": 2, "math": 3, "reading": 3},
            "borealis-13b": {"logic": 3, "math": 3, "reading": 2},
            "cirrus-3b": {"logic": 3, "math": 2, "reading": 2},
        })

    def test_leaderboard(self):
        self.assertEqual(self.report["leaderboard"], ["borealis-13b", "atlas-7b", "cirrus-3b"])


if __name__ == "__main__":
    unittest.main()
