import unittest

from splitkit.reports import build_report


class TestSplits(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_doc_assignment(self):
        self.assertEqual(self.report["doc_splits"], {
            "doc-01": "train", "doc-02": "val", "doc-03": "val", "doc-04": "train",
            "doc-05": "test", "doc-06": "val", "doc-07": "train", "doc-08": "train",
            "doc-09": "test", "doc-10": "train", "doc-11": "val", "doc-12": "train",
        })

    def test_pinned_doc_goes_to_test(self):
        self.assertEqual(self.report["doc_splits"].get("doc-09"), "test")

    def test_val_sample(self):
        self.assertEqual(self.report["val_sample"], {
            "negative": ["I005", "I010"],
            "neutral": ["I008", "I029"],
            "positive": ["I004", "I006"],
        })


if __name__ == "__main__":
    unittest.main()
