import unittest

from quorum.reports import build_report


class TestScreening(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_rejected_by_vendor(self):
        self.assertEqual(self.report["rejected"], {
            "vendor_a": {"A-010": "inactive", "A-011": "not_certified", "A-027": "unknown_item",
                         "A-028": "inactive", "A-030": "invalid_label"},
            "vendor_b": {"b-1019": "unknown_annotator", "b-1020": "not_certified",
                         "b-1021": "not_certified", "b-1022": "invalid_label"},
        })

    def test_superseded(self):
        self.assertEqual(self.report["superseded"], ["A-003", "A-016"])

    def test_quality_vote_counts(self):
        items = self.report["queues"]["quality"]["items"]
        self.assertEqual({iid: r["votes"] for iid, r in items.items()},
                         {"Q01": 3, "Q02": 4, "Q03": 3, "Q04": 5, "Q05": 2})


if __name__ == "__main__":
    unittest.main()
