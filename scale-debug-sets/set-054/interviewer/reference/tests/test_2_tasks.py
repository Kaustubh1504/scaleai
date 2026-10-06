import unittest

from reviewflow.reports import build_report


class TestTasks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_history(self):
        history = self.report["history"]
        self.assertEqual(history["T1"], ["submitted", "l1_review", "awaiting_l2", "l2_review", "approved"])
        self.assertEqual(history["T3"], ["submitted", "l1_review", "changes_requested", "submitted",
                                         "l1_review", "awaiting_l2", "l2_review", "approved"])
        self.assertEqual(history["T10"], ["submitted"])

    def test_waiting_queue(self):
        self.assertEqual(self.report["queue"], [
            ["T2", "submitted"],
            ["T11", "submitted"],
            ["T12", "submitted"],
            ["T7", "awaiting_l2"],
            ["T10", "submitted"],
        ])

    def test_reviewer_stats(self):
        self.assertEqual(self.report["reviewers"], {
            "dana": {"passed": 2, "changes": 1, "rejected": 0},
            "lee": {"passed": 2, "changes": 0, "rejected": 1},
            "rae": {"passed": 3, "changes": 1, "rejected": 1},
            "sam": {"passed": 3, "changes": 0, "rejected": 1},
        })


if __name__ == "__main__":
    unittest.main()
