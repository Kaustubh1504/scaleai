import unittest

from episodekit.reports import build_report


class TestReport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.summary = build_report()["summary"]

    def test_totals(self):
        self.assertEqual((self.summary["total"], self.summary["valid"]), (14, 8))

    def test_valid_by_task(self):
        self.assertEqual(self.summary["valid_by_task"], {"pick": 3, "place": 3, "stack": 2})

    def test_valid_by_day(self):
        self.assertEqual(self.summary["valid_by_day"],
                         {"2026-04-02": 2, "2026-04-03": 3, "2026-04-04": 1, "2026-04-05": 2})

    def test_invalid_reasons(self):
        self.assertEqual(self.summary["invalid_reasons"], {
            "desync": 1, "frame_gap": 1, "missing_stream": 1, "robot_unavailable": 2, "too_short": 1,
        })

    def test_sync_and_duration(self):
        self.assertEqual((self.summary["mean_sync_ratio"], self.summary["valid_duration_s"]), (0.967, 4.4))


if __name__ == "__main__":
    unittest.main()
