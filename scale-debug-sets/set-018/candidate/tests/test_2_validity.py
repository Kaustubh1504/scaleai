import unittest

from teleop.reports import build_report


class TestValidity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.episodes = build_report()["episodes"]

    def with_reason(self, reason):
        return sorted(eid for eid, e in self.episodes.items() if reason in e["reasons"])

    def test_valid_episodes(self):
        valid = sorted(eid for eid, e in self.episodes.items() if not e["reasons"])
        self.assertEqual(valid, ["EP01", "EP02", "EP03", "EP07", "EP10", "EP11", "EP12"])

    def test_short_and_unsynced(self):
        self.assertEqual((self.with_reason("too_short"), self.with_reason("unsynced")),
                         (["EP04", "EP05"], ["EP06", "EP09"]))

    def test_4_inactive_robots(self):
        self.assertEqual(self.with_reason("robot_inactive"), ["EP05", "EP09"])

    def test_5_frame_gaps(self):
        self.assertEqual(self.with_reason("frame_gap"), ["EP08"])


if __name__ == "__main__":
    unittest.main()
