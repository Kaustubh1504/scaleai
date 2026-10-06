import unittest

from ratingpanel.reports import build_report


class TestSummary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.summary = build_report()["summary"]

    def test_status_counts(self):
        self.assertEqual(self.summary["status_counts"],
                         {"adjudicated": 1, "agreed": 6, "escalated": 2, "insufficient": 3})

    def test_5_category_means(self):
        means = self.summary["category_means"]
        self.assertEqual({"coding": means.get("coding"), "writing": means.get("writing")},
                         {"coding": 5.67, "writing": 6.67})

    def test_6_escalated_items(self):
        self.assertEqual(self.summary["escalated"], ["I-02", "I-10"])


if __name__ == "__main__":
    unittest.main()
