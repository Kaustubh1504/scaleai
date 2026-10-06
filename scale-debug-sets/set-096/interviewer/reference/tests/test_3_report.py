import unittest

from holdout.reports import build_report


class TestReport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_dataset_order(self):
        self.assertEqual(list(self.report), ["intent", "toxicity", "summaries"])

    def test_targets(self):
        self.assertEqual({name: ds["targets"] for name, ds in self.report.items()}, {
            "intent": {"train": 9, "val": 3, "test": 3},
            "toxicity": {"train": 10, "val": 4, "test": 6},
            "summaries": {"train": 8, "val": 2, "test": 2},
        })

    def test_label_totals(self):
        self.assertEqual({name: ds["label_totals"] for name, ds in self.report.items()}, {
            "intent": {"book_flight": 4, "cancel": 4, "greet": 2, "refund": 5},
            "toxicity": {"borderline": 5, "safe": 9, "toxic": 6},
            "summaries": {"faithful": 5, "hallucinated": 4, "partial": 3},
        })


if __name__ == "__main__":
    unittest.main()
