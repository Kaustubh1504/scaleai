import unittest

from ratingpanel.reports import build_report

STATUSES = {
    "I-01": "insufficient", "I-02": "escalated", "I-03": "agreed", "I-04": "agreed",
    "I-05": "insufficient", "I-06": "agreed", "I-07": "agreed", "I-08": "agreed",
    "I-09": "agreed", "I-10": "escalated", "I-11": "adjudicated", "I-12": "insufficient",
}


class TestConsensus(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_statuses(self):
        self.assertEqual({iid: row["status"] for iid, row in self.report["items"].items()}, STATUSES)

    def test_3_consensus_values(self):
        got = {iid: row["consensus"] for iid, row in self.report["items"].items()}
        self.assertEqual(got, {
            "I-01": None, "I-02": 6, "I-03": 4, "I-04": 7, "I-05": None, "I-06": 6.5,
            "I-07": 5, "I-08": 8, "I-09": 6, "I-10": 5, "I-11": 9, "I-12": None,
        })

    def test_4_outlier_counts(self):
        got = {aid: row["outliers"] for aid, row in self.report["annotators"].items() if row["outliers"]}
        self.assertEqual(got, {"ann-03": 1, "ann-04": 1, "ann-05": 1})


if __name__ == "__main__":
    unittest.main()
