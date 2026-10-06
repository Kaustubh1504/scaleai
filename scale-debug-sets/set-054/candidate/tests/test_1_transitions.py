import unittest

from reviewflow.reports import build_report


class TestTransitions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_final_states(self):
        self.assertEqual(self.report["states"], {
            "T1": "approved", "T2": "submitted", "T3": "approved", "T4": "approved",
            "T5": "rejected", "T6": "approved", "T7": "awaiting_l2", "T8": "rejected",
            "T9": "rejected", "T10": "submitted", "T11": "submitted", "T12": "submitted",
        })

    def test_revisions(self):
        resubmitted = {t: n for t, n in self.report["revisions"].items() if n > 1}
        self.assertEqual(resubmitted, {"T2": 2, "T3": 2})

    def test_rejected_events(self):
        self.assertEqual([row[:4] for row in self.report["rejected"]], [
            ["2026-07-06 10:20", "T1", "rae", "claim"],
            ["2026-07-06 10:30", "T3", "cho", "claim"],
            ["2026-07-06 11:30", "T4", "lee", "pass"],
            ["2026-07-06 16:30", "T6", "lee", "pass"],
            ["2026-07-07 12:00", "T99", "ben", "claim"],
            ["2026-07-07 12:10", "T8", "eli", "claim"],
            ["2026-07-07 13:00", "T1", "ann", "approve"],
            ["2026-07-07 13:05", "T2", "dana", "resubmit"],
        ])

    def test_rejection_reasons(self):
        self.assertEqual([row[4] for row in self.report["rejected"]], [
            "conflict_of_interest",
            "conflict_of_interest",
            "invalid_transition",
            "not_assignee",
            "unknown_task",
            "conflict_of_interest",
            "invalid_transition",
            "invalid_transition",
        ])


if __name__ == "__main__":
    unittest.main()
