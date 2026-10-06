import unittest

from episodeqa.report import build_report


class TestReport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.summary = build_report()["summary"]

    def test_totals(self):
        self.assertEqual((self.summary["valid_episodes"], self.summary["valid_hours"]), (8, 0.0068))

    def test_success_rate(self):
        self.assertEqual(self.summary["success_rate"],
                         {"fold_towel": 0.0, "open_drawer": 0.5, "pick_place": 0.75, "wipe_table": 0.0})

    def test_operators(self):
        self.assertEqual(self.summary["operators"], {
            "ana": {"submitted": 4, "valid": 2, "valid_s": 5.0},
            "ben": {"submitted": 4, "valid": 2, "valid_s": 6.5},
            "chen": {"submitted": 4, "valid": 3, "valid_s": 10.0},
            "dara": {"submitted": 4, "valid": 1, "valid_s": 3.0},
        })


if __name__ == "__main__":
    unittest.main()
