import unittest

from episodeqa.report import build_report

EXPECTED = {
    "E01": None, "E02": None, "E03": None, "E04": None, "E05": None, "E06": None,
    "E07": None, "E08": "dropped_frames", "E09": "too_short", "E10": "uncalibrated",
    "E11": "missing_stream", "E12": "unlabelled", "E13": "unknown_robot",
    "E14": "out_of_sync", "E15": None, "E16": "too_long",
}


class TestValidity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.episodes = build_report()["episodes"]

    def test_registry_checks(self):
        self.assertEqual(self.episodes["E13"]["reason"], "unknown_robot")
        self.assertEqual(self.episodes["E10"]["reason"], "uncalibrated")
        self.assertEqual(self.episodes["E11"]["reason"], "missing_stream")

    def test_reasons(self):
        self.maxDiff = None
        self.assertEqual({eid: row["reason"] for eid, row in self.episodes.items()}, EXPECTED)

    def test_valid_flags_match_reasons(self):
        for eid, row in self.episodes.items():
            self.assertEqual(row["valid"], row["reason"] is None, eid)


if __name__ == "__main__":
    unittest.main()
