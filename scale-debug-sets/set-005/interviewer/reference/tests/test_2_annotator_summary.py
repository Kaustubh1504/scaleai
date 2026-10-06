import unittest

from boxqa.reports import build_report


class TestAnnotatorSummary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.annotators = build_report()["annotators"]

    def test_images_reviewed(self):
        self.assertEqual({a: s["images"] for a, s in self.annotators.items()},
                         {"alice": 5, "bob": 6, "chen": 4})

    def test_summary(self):
        self.maxDiff = None
        self.assertEqual(self.annotators, {
            "alice": {"images": 5, "tp": 8, "fp": 1, "fn": 2, "precision": 0.889, "recall": 0.8},
            "bob": {"images": 6, "tp": 8, "fp": 2, "fn": 2, "precision": 0.8, "recall": 0.8},
            "chen": {"images": 4, "tp": 6, "fp": 2, "fn": 2, "precision": 0.75, "recall": 0.75},
        })


if __name__ == "__main__":
    unittest.main()
