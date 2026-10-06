import unittest

from podium.ranking import build_report


class TestTeamScores(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.teams = build_report()["teams"]

    def test_ranked_teams(self):
        self.assertEqual(sorted(self.teams),
                         ["T01", "T02", "T03", "T04", "T05", "T08", "T09", "T10", "T11", "T12"])

    def test_1_best_scores(self):
        self.assertEqual({tid: t["best_score"] for tid, t in self.teams.items()}, {
            "T01": 85.0, "T02": 82.9, "T03": 82.5, "T04": 82.5, "T05": 57.0,
            "T08": 83.3, "T09": 81.8, "T10": 73.3, "T11": 76.7, "T12": 37.5,
        })

    def test_2_accepted_counts(self):
        self.assertEqual({tid: t["accepted"] for tid, t in self.teams.items()}, {
            "T01": 2, "T02": 2, "T03": 2, "T04": 2, "T05": 2,
            "T08": 3, "T09": 1, "T10": 1, "T11": 2, "T12": 1,
        })


if __name__ == "__main__":
    unittest.main()
