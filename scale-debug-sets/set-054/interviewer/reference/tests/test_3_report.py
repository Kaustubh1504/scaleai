import unittest

from reviewflow.reports import build_report


class TestReport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_cycle_hours(self):
        self.assertEqual(self.report["cycle_hours"], {
            "T1": 2.2, "T3": 24.5, "T4": 6.0, "T5": 3.5, "T6": 21.5, "T8": 23.7, "T9": 3.0,
        })

    def test_state_counts(self):
        self.assertEqual(self.report["summary"]["by_state"],
                         {"approved": 4, "awaiting_l2": 1, "rejected": 3, "submitted": 4})

    def test_approval_rate(self):
        self.assertEqual(self.report["summary"]["approval_rate"], 0.571)


if __name__ == "__main__":
    unittest.main()
