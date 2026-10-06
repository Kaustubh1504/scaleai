import unittest

from ladder.teams import build_report

EXPECTED = [
    {"rank": 1, "contributor_id": "c-12", "name": "Lia Romero", "score": 23, "tasks_solved": 3, "attempts": 3},
    {"rank": 2, "contributor_id": "c-01", "name": "Ava Brooks", "score": 21, "tasks_solved": 3, "attempts": 3},
    {"rank": 2, "contributor_id": "c-02", "name": "Ben Okafor", "score": 21, "tasks_solved": 3, "attempts": 3},
    {"rank": 4, "contributor_id": "c-04", "name": "Dara Singh", "score": 20, "tasks_solved": 3, "attempts": 3},
    {"rank": 5, "contributor_id": "c-06", "name": "Fay Lindqvist", "score": 19, "tasks_solved": 3, "attempts": 3},
    {"rank": 6, "contributor_id": "c-03", "name": "Chen Wei", "score": 17, "tasks_solved": 2, "attempts": 3},
    {"rank": 7, "contributor_id": "c-11", "name": "Kai Nakamura", "score": 14, "tasks_solved": 2, "attempts": 2},
    {"rank": 8, "contributor_id": "c-10", "name": "Jo Mensah", "score": 13, "tasks_solved": 2, "attempts": 2},
    {"rank": 9, "contributor_id": "c-09", "name": "Ivo Petrov", "score": 13, "tasks_solved": 2, "attempts": 3},
    {"rank": 10, "contributor_id": "c-08", "name": "Hana Sato", "score": 9, "tasks_solved": 1, "attempts": 1},
    {"rank": 11, "contributor_id": "c-07", "name": "Gus Ferreira", "score": 4, "tasks_solved": 1, "attempts": 1},
]


class TestLeaderboard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_banned_and_unknown_excluded(self):
        ids = {row["contributor_id"] for row in self.report["leaderboard"]}
        self.assertFalse(ids & {"c-05", "c-13", "c-99", "c-14"})

    def test_order(self):
        self.assertEqual([r["contributor_id"] for r in self.report["leaderboard"]],
                         [r["contributor_id"] for r in EXPECTED])

    def test_scores(self):
        self.assertEqual({r["contributor_id"]: r["score"] for r in self.report["leaderboard"]},
                         {r["contributor_id"]: r["score"] for r in EXPECTED})

    def test_full_rows(self):
        self.maxDiff = None
        self.assertEqual(self.report["leaderboard"], EXPECTED)


if __name__ == "__main__":
    unittest.main()
