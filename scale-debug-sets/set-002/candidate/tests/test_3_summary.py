import unittest

from consensus.reports import build_report


class TestSummary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.summary = build_report()["summary"]

    def test_label_counts(self):
        self.assertEqual(self.summary["label_counts"], {"bird": 2, "cat": 2, "dog": 1, "fish": 2})

    def test_needs_more_votes(self):
        self.assertEqual(self.summary["needs_more_votes"], ["T08", "T11"])

    def test_most_disputed(self):
        self.assertEqual(self.summary["most_disputed"], "T03")


if __name__ == "__main__":
    unittest.main()
