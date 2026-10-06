import unittest

from spanalign.reports import build_report


class TestAgreementReport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_annotator_scores(self):
        self.maxDiff = None
        self.assertEqual(self.report["scores"], {
            "ann-a": {"tp": 7, "fp": 1, "fn": 2, "precision": 0.875, "recall": 0.778, "f1": 0.824},
            "ann-b": {"tp": 4, "fp": 4, "fn": 10, "precision": 0.5, "recall": 0.286, "f1": 0.364},
            "ann-c": {"tp": 5, "fp": 1, "fn": 6, "precision": 0.833, "recall": 0.455, "f1": 0.588},
        })

    def test_label_confusions(self):
        self.assertEqual(self.report["confusions"], [["LOC", "ORG", 2], ["ORG", "LOC", 2], ["PERSON", "ORG", 1]])

    def test_gold_label_counts(self):
        self.assertEqual(self.report["gold_labels"], {"DATE": 3, "LOC": 7, "ORG": 6, "PERSON": 5})


if __name__ == "__main__":
    unittest.main()
