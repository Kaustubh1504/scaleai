import unittest

from revflow.reports import build_report


def v(line, task, action, reason):
    return {"line": line, "task": task, "action": action, "reason": reason}


class TestLifecycle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_final_states(self):
        self.maxDiff = None
        self.assertEqual(self.report["states"], {
            "T-01": "approved", "T-02": "approved", "T-03": "approved", "T-04": "submitted",
            "T-05": "submitted", "T-06": "submitted", "T-07": "submitted", "T-08": "submitted",
            "T-09": "submitted", "T-10": "in_review", "T-11": "submitted", "T-12": "in_review",
            "T-13": "labeling", "T-14": "queued",
        })

    def test_rework_counts(self):
        self.assertEqual(self.report["rework"], {"T-02": 1, "T-03": 2})

    def test_violations(self):
        self.maxDiff = None
        self.assertEqual(self.report["violations"], [
            v(18, "T-03", "resolve", "actor not allowed"),
            v(23, "T-04", "claim_review", "actor not allowed"),
            v(25, "T-05", "approve", "not claim holder"),
            v(26, "T-99", "submit", "unknown task"),
            v(30, "T-13", "claim_label", "actor not allowed"),
            v(32, "T-14", "claim_review", "invalid transition"),
            v(29, "T-11", "approve", "invalid transition"),
            v(33, "T-12", "claim_review", "actor not allowed"),
        ])


if __name__ == "__main__":
    unittest.main()
