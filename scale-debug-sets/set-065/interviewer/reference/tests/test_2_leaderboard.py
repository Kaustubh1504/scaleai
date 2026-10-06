import unittest

from podium.board import build_board


class TestLeaderboard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.board = build_board()

    def test_ranking(self):
        got = [(r["rank"], r["team_id"]) for r in self.board["leaderboard"]]
        self.assertEqual(got, [
            (1, "ember"), (2, "basalt"), (3, "aurora"), (3, "cobalt"), (5, "s-iris"),
            (6, "s-koi"), (7, "s-hydra"), (8, "dynamo"), (9, "s-jade"), (10, "garnet"), (11, "s-lumen"),
        ])

    def test_podiums(self):
        self.assertEqual(self.board["podiums"], {
            "open": ["ember", "basalt", "aurora"],
            "student": ["s-iris", "s-koi", "s-hydra"],
        })

    def test_3_submission_counts(self):
        summary = self.board["summary"]
        self.assertEqual(summary["teams"], 11)
        self.assertEqual(summary["counted_submissions"], 31)
        self.assertEqual(summary["submissions_by_task"], {"gsm8k": 11, "humaneval": 9, "mmlu": 11})


if __name__ == "__main__":
    unittest.main()
