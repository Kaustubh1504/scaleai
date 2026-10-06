import unittest

from ladder.teams import build_report


class TestTeams(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_team_order(self):
        self.assertEqual([t["team"] for t in self.report["teams"]], ["Falcons", "Herons", "Otters", "Lynx"])

    def test_team_scores(self):
        self.assertEqual({t["team"]: (t["score"], t["members"]) for t in self.report["teams"]},
                         {"Falcons": (42, 3), "Herons": (37, 2), "Otters": (37, 3), "Lynx": (32, 3)})

    def test_summary(self):
        self.assertEqual(self.report["summary"], {
            "submissions_counted": 27,
            "contributors_ranked": 11,
            "leader": "c-12",
            "top_team": "Falcons",
        })


if __name__ == "__main__":
    unittest.main()
