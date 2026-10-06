import unittest

from episodekit.reports import build_report


class TestValidity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.episodes = build_report()["episodes"]

    def test_valid_episodes(self):
        valid = sorted(eid for eid, row in self.episodes.items() if row["valid"])
        self.assertEqual(valid, ["EP-01", "EP-02", "EP-03", "EP-05", "EP-07", "EP-09", "EP-13", "EP-14"])

    def test_rejection_reasons(self):
        rejected = {eid: row["reason"] for eid, row in self.episodes.items() if not row["valid"]}
        self.assertEqual(rejected, {
            "EP-04": "robot_unavailable",
            "EP-06": "too_short",
            "EP-08": "frame_gap",
            "EP-10": "missing_stream",
            "EP-11": "desync",
            "EP-12": "robot_unavailable",
        })


if __name__ == "__main__":
    unittest.main()
