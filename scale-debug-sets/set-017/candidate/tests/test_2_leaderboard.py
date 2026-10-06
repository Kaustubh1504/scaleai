import unittest

from podium.ranking import build_report


class TestLeaderboard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.board = build_report()["leaderboard"]

    def test_podium(self):
        self.assertEqual(self.board[:3], [[1, "T01"], [2, "T08"], [3, "T02"]])

    def test_last_place(self):
        self.assertEqual(self.board[-1], [10, "T12"])

    def test_3_full_leaderboard(self):
        self.assertEqual(self.board, [
            [1, "T01"], [2, "T08"], [3, "T02"], [4, "T04"], [5, "T03"],
            [6, "T09"], [7, "T11"], [8, "T10"], [9, "T05"], [10, "T12"],
        ])


if __name__ == "__main__":
    unittest.main()
