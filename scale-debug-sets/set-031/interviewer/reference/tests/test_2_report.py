import unittest

from evalscore.reports import build_report


class TestReport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_by_category(self):
        got = {m: r["by_category"] for m, r in self.report["models"].items()}
        self.assertEqual(got, {
            "atlas-7b": {"logic": 0.75, "math": 0.667, "reading": 0.444},
            "boreal-13b": {"logic": 0.5, "math": 0.833, "reading": 0.556},
        })

    def test_status_counts(self):
        self.assertEqual(self.report["status_counts"], {
            "atlas-7b": {"ok": 11, "error": 4, "timeout": 2},
            "boreal-13b": {"ok": 11, "error": 4, "timeout": 2},
        })

    def test_leaderboard(self):
        self.assertEqual(self.report["leaderboard"], ["boreal-13b", "atlas-7b"])


if __name__ == "__main__":
    unittest.main()
