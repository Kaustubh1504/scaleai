import unittest

from evalboard.report import build_leaderboard


class TestScores(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = build_leaderboard()
        cls.rows = {row["team"]: row for row in cls.result["board"]}

    def test_board_members(self):
        self.assertEqual(sorted(self.rows),
                         ["heron", "kelp", "lynx", "marten", "narwhal", "orca", "otter", "puffin", "wren"])
        self.assertEqual(self.result["excluded_teams"], ["fox", "moth"])

    def test_top_team_bests(self):
        self.assertEqual(self.rows["kelp"]["bests"],
                         {"reasoning": 64.0, "coding": 45.0, "latency_ms": 200.0, "safety": 81.0})
        self.assertEqual(self.rows["narwhal"]["bests"],
                         {"reasoning": 80.0, "coding": 40.0, "latency_ms": 250.0, "safety": 72.0})

    def test_partial_entrants(self):
        self.assertEqual(self.rows["wren"]["composite"], 0.25)
        self.assertEqual(self.rows["marten"]["composite"], 0.1667)
        self.assertEqual(self.rows["lynx"]["composite"], 0.6667)

    def test_1_mid_table_composites(self):
        got = {t: (self.rows[t]["composite"], self.rows[t]["bests"].get("reasoning"))
               for t in ("puffin", "otter", "orca")}
        self.assertEqual(got, {"puffin": (0.75, 60.0), "otter": (0.7333, 72.0), "orca": (0.7, 48.0)})


if __name__ == "__main__":
    unittest.main()
