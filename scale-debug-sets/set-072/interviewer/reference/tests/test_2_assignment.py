import unittest

from voxsplit.reports import build_report

HELD_OUT = ("S08", "S09", "S19")
REGULAR = {
    "S01": "train", "S02": "train", "S03": "train", "S04": "train", "S05": "train",
    "S06": "train", "S07": "test", "S10": "val", "S11": "test", "S12": "val",
    "S13": "train", "S14": "train", "S15": "train", "S16": "train", "S17": "test",
    "S18": "train", "S20": "val", "S21": "train",
}


class TestAssignment(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_strata_sizes(self):
        self.assertEqual(self.report["strata"], {"au": 3, "in": 4, "uk": 7, "us": 7})

    def test_held_out_speakers_in_test(self):
        got = {sid: self.report["assignment"].get(sid) for sid in HELD_OUT}
        self.assertEqual(got, {sid: "test" for sid in HELD_OUT})

    def test_regular_speakers(self):
        got = {sid: split for sid, split in self.report["assignment"].items() if sid not in HELD_OUT}
        self.assertEqual(got, REGULAR)


if __name__ == "__main__":
    unittest.main()
