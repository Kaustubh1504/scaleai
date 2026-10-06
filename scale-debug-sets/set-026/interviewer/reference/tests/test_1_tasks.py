import unittest

from tonevote.reports import build_report


class TestTasks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tasks = build_report()["tasks"]

    def test_task_ids(self):
        self.assertEqual(sorted(self.tasks), [
            "C-01", "C-02", "C-03", "C-04", "C-05", "C-06", "C-07",
            "E-01", "E-02", "E-03", "E-04", "E-05", "E-06",
            "R-01", "R-02", "R-03", "R-04", "R-05",
        ])

    def test_vote_counts(self):
        votes = {tid: t["votes"] for tid, t in self.tasks.items()}
        self.assertEqual(votes, {
            "C-01": 4, "C-02": 4, "C-03": 3, "C-04": 4, "C-05": 5, "C-06": 2, "C-07": 4,
            "E-01": 2, "E-02": 3, "E-03": 3, "E-04": 1, "E-05": 3, "E-06": 3,
            "R-01": 4, "R-02": 5, "R-03": 5, "R-04": 5, "R-05": 2,
        })

    def test_statuses(self):
        statuses = {tid: t["status"] for tid, t in self.tasks.items()}
        self.assertEqual(statuses, {
            "C-01": "agreed", "C-02": "agreed", "C-03": "escalated", "C-04": "escalated",
            "C-05": "agreed", "C-06": "pending", "C-07": "agreed",
            "E-01": "escalated", "E-02": "agreed", "E-03": "agreed", "E-04": "pending",
            "E-05": "agreed", "E-06": "escalated",
            "R-01": "escalated", "R-02": "agreed", "R-03": "agreed", "R-04": "agreed",
            "R-05": "pending",
        })

    def test_agreed_labels(self):
        labels = {tid: t["label"] for tid, t in self.tasks.items() if t["status"] == "agreed"}
        self.assertEqual(labels, {
            "C-01": "positive", "C-02": "negative", "C-05": "positive", "C-07": "positive",
            "E-02": "positive", "E-03": "neutral", "E-05": "negative",
            "R-02": "positive", "R-03": "negative", "R-04": "neutral",
        })


if __name__ == "__main__":
    unittest.main()
