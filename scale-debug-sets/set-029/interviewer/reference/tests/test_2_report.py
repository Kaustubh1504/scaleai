import unittest

from boxaudit.reports import build_report


class TestReport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_annotator_scores(self):
        self.maxDiff = None
        self.assertEqual(self.report["annotators"], {
            "ann-1": {"tp": 8, "fp": 0, "fn": 2, "precision": 1.0, "recall": 0.8, "f1": 0.889},
            "ann-2": {"tp": 5, "fp": 3, "fn": 5, "precision": 0.625, "recall": 0.5, "f1": 0.556},
            "ann-3": {"tp": 4, "fp": 2, "fn": 6, "precision": 0.667, "recall": 0.4, "f1": 0.5},
        })

    def test_localization(self):
        self.assertEqual(self.report["localization"], {"car": 0.971, "person": 0.944, "sign": 0.701})


if __name__ == "__main__":
    unittest.main()
