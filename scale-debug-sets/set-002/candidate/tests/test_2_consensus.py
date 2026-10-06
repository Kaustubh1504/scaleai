import unittest

from consensus.reports import build_report

EXPECTED = {
    "T03": {"status": "resolved", "label": "cat", "confidence": 0.5, "votes": 3},
    "T04": {"status": "resolved", "label": "dog", "confidence": 1.0, "votes": 2},
    "T05": {"status": "resolved", "label": "bird", "confidence": 1.0, "votes": 2},
    "T06": {"status": "resolved", "label": "fish", "confidence": 0.667, "votes": 2},
    "T07": {"status": "resolved", "label": "cat", "confidence": 0.5, "votes": 2},
    "T08": {"status": "needs_more_votes", "label": None, "confidence": None, "votes": 1},
    "T09": {"status": "resolved", "label": "fish", "confidence": 1.0, "votes": 3},
    "T10": {"status": "resolved", "label": "bird", "confidence": 0.5, "votes": 3},
    "T11": {"status": "needs_more_votes", "label": None, "confidence": None, "votes": 0},
}


class TestConsensus(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_gold_tasks_not_in_consensus(self):
        self.assertNotIn("T01", self.report["consensus"])
        self.assertNotIn("T02", self.report["consensus"])

    def test_labels(self):
        labels = {tid: r["label"] for tid, r in self.report["consensus"].items()}
        self.assertEqual(labels, {tid: r["label"] for tid, r in EXPECTED.items()})

    def test_full_consensus(self):
        self.maxDiff = None
        self.assertEqual(self.report["consensus"], EXPECTED)


if __name__ == "__main__":
    unittest.main()
