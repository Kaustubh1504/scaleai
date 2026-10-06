import unittest

from episodeqa.report import build_report


class TestDataset(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_durations(self):
        durations = {eid: row["duration_s"] for eid, row in self.report["episodes"].items()}
        self.assertEqual(durations, {
            "E01": 3.0, "E02": 4.0, "E03": 2.5, "E04": 2.0, "E05": 3.0, "E06": 2.5,
            "E07": 2.5, "E08": 1.87, "E09": 1.0, "E10": None, "E11": None, "E12": 2.0,
            "E13": None, "E14": 2.0, "E15": 5.0, "E16": 13.0,
        })

    def test_task_table(self):
        self.assertEqual(self.report["tasks"], {
            "fold_towel": {"episodes": ["E15"], "total_s": 5.0},
            "open_drawer": {"episodes": ["E04", "E06"], "total_s": 4.5},
            "pick_place": {"episodes": ["E01", "E03", "E05", "E07"], "total_s": 11.0},
            "wipe_table": {"episodes": ["E02"], "total_s": 4.0},
        })


if __name__ == "__main__":
    unittest.main()
