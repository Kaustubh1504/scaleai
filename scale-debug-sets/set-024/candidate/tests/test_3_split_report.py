import unittest

from splitkit.reports import build_report


class TestSplitReport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_split = build_report()["splits"]["test"]

    def test_test_split_size(self):
        self.assertEqual(self.test_split["size"], 6)

    def test_test_split_labels(self):
        self.assertEqual(self.test_split["labels"], {"negative": 2, "neutral": 2, "positive": 2})

    def test_test_split_avg_tokens(self):
        self.assertEqual(self.test_split["avg_tokens"], 4.83)


if __name__ == "__main__":
    unittest.main()
