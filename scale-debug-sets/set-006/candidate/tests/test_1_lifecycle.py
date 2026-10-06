import unittest

from reviewflow.reports import build_report

STATES = {
    "T01": "approved", "T02": "approved", "T03": "approved", "T04": "escalated",
    "T05": "submitted", "T06": "claimed", "T07": "queued", "T08": "approved",
    "T09": "queued", "T10": "submitted", "T11": "approved", "T12": "queued",
}
TRANSITIONS = {
    "T01": 3, "T02": 6, "T03": 3, "T04": 9, "T05": 2, "T06": 1,
    "T07": 2, "T08": 3, "T09": 0, "T10": 2, "T11": 3, "T12": 0,
}


class TestLifecycle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_final_states(self):
        self.maxDiff = None
        got = {tid: row["state"] for tid, row in self.report["tasks"].items()}
        self.assertEqual(got, STATES)

    def test_rework_and_assignees(self):
        got = {tid: (row["rework"], row["assignee"]) for tid, row in self.report["tasks"].items()
               if tid in ("T02", "T04", "T05", "T06", "T07")}
        self.assertEqual(got, {
            "T02": (1, "ann-02"), "T04": (3, None), "T05": (0, "ann-02"),
            "T06": (0, "ann-05"), "T07": (0, None),
        })

    def test_transition_counts(self):
        self.maxDiff = None
        got = {tid: row["transitions"] for tid, row in self.report["tasks"].items()}
        self.assertEqual(got, TRANSITIONS)

    def test_invalid_events(self):
        self.assertEqual(self.report["invalid"], ["E11", "E17", "E33", "E36", "E40", "E38"])


if __name__ == "__main__":
    unittest.main()
