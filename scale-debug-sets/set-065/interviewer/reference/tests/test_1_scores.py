import unittest

from podium.board import build_board


class TestScores(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = {r["team_id"]: r for r in build_board()["leaderboard"]}

    def test_registered_teams(self):
        self.assertEqual(sorted(self.rows), [
            "aurora", "basalt", "cobalt", "dynamo", "ember", "garnet",
            "s-hydra", "s-iris", "s-jade", "s-koi", "s-lumen",
        ])

    def test_1_team_scores(self):
        got = {t: r["score"] for t, r in self.rows.items()}
        self.assertEqual(got, {
            "ember": 88.33, "basalt": 81.17, "aurora": 80.17, "cobalt": 80.17,
            "s-iris": 72.5, "s-koi": 72.17, "s-hydra": 68.33, "dynamo": 60.33,
            "s-jade": 50.0, "garnet": 18.33, "s-lumen": 0.0,
        })
        self.assertEqual(self.rows["basalt"]["best"], {"gsm8k": 100.0, "humaneval": 64.0, "mmlu": 79.5})

    def test_2_tasks_attempted(self):
        got = {t: r["tasks_attempted"] for t, r in self.rows.items()}
        self.assertEqual(got, {
            "aurora": 3, "basalt": 3, "cobalt": 3, "dynamo": 2, "ember": 3, "garnet": 1,
            "s-hydra": 3, "s-iris": 3, "s-jade": 3, "s-koi": 3, "s-lumen": 0,
        })


if __name__ == "__main__":
    unittest.main()
