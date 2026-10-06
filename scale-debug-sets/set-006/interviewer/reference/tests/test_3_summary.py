import unittest

from reviewflow.reports import build_report


class TestSummary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.summary = build_report()["summary"]

    def test_state_counts(self):
        self.assertEqual(self.summary["state_counts"],
                         {"queued": 3, "claimed": 1, "submitted": 2, "approved": 5, "escalated": 1})

    def test_first_pass_rate(self):
        self.assertEqual(self.summary["first_pass_rate"], 0.8)

    def test_avg_cycle_hours(self):
        self.assertEqual(self.summary["avg_cycle_hours"], 24.5)

    def test_open_by_queue(self):
        self.assertEqual(self.summary["open_by_queue"], {"audio": 1, "image": 2, "text": 3})


if __name__ == "__main__":
    unittest.main()
