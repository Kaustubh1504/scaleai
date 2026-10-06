import unittest

from likert.reports import build_report

EXPECTED = {
    "I01": {"status": "agreed", "score": 4.0, "agreement": 1.0, "votes": 4},
    "I02": {"status": "agreed", "score": 2.75, "agreement": 1.0, "votes": 4},
    "I03": {"status": "agreed", "score": 4.0, "agreement": 0.6, "votes": 5},
    "I04": {"status": "contested", "score": 3.0, "agreement": 0.333, "votes": 3},
    "I05": {"status": "agreed", "score": 2.0, "agreement": 1.0, "votes": 3},
    "I06": {"status": "agreed", "score": 4.25, "agreement": 1.0, "votes": 4},
    "I07": {"status": "contested", "score": 3.25, "agreement": 0.5, "votes": 4},
    "I08": {"status": "agreed", "score": 4.5, "agreement": 0.75, "votes": 4},
    "I09": {"status": "contested", "score": 2.5, "agreement": 0.5, "votes": 4},
    "I10": {"status": "agreed", "score": 3.0, "agreement": 0.667, "votes": 3},
    "I11": {"status": "insufficient", "score": None, "agreement": None, "votes": 1},
    "I12": {"status": "agreed", "score": 3.75, "agreement": 1.0, "votes": 4},
}


class TestConsensus(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.consensus = build_report()["consensus"]

    def test_gold_items_excluded(self):
        self.assertEqual(sorted(self.consensus), sorted(EXPECTED))

    def test_vote_counts(self):
        self.assertEqual({k: v["votes"] for k, v in self.consensus.items()},
                         {k: v["votes"] for k, v in EXPECTED.items()})

    def test_scores(self):
        self.assertEqual({k: v["score"] for k, v in self.consensus.items()},
                         {k: v["score"] for k, v in EXPECTED.items()})

    def test_full_consensus(self):
        self.maxDiff = None
        self.assertEqual(self.consensus, EXPECTED)


if __name__ == "__main__":
    unittest.main()
