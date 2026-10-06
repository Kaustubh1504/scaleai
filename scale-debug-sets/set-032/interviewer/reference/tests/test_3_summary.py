import unittest

from vendorfeed.reports import build_report


class TestSummary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.summary = build_report()["summary"]

    def test_label_counts(self):
        self.assertEqual(self.summary["label_counts"],
                         {"mixed": 1, "negative": 7, "neutral": 6, "positive": 8})

    def test_tag_counts(self):
        self.assertEqual(self.summary["tag_counts"],
                         {"long": 7, "sarcasm": 5, "sentiment": 7, "short": 9})

    def test_by_batch(self):
        self.assertEqual(self.summary["by_batch"], {
            "b1": 3, "b2": 3, "b3": 1, "b4": 4, "b5": 3, "b6": 5, "unbatched": 3,
        })


if __name__ == "__main__":
    unittest.main()
