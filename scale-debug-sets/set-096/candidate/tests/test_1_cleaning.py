import unittest

from holdout.reports import build_report


class TestCleaning(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_kept_counts(self):
        self.assertEqual({name: ds["kept"] for name, ds in self.report.items()},
                         {"intent": 15, "toxicity": 20, "summaries": 12})

    def test_drop_reasons(self):
        self.maxDiff = None
        self.assertEqual({name: ds["dropped"] for name, ds in self.report.items()}, {
            "intent": {"IN-05": "blocked_source", "IN-09": "low_quality",
                       "IN-14": "blocked_source", "IN-17": "incomplete"},
            "toxicity": {"TX-07": "blocked_source", "TX-08": "blocked_source",
                         "TX-14": "low_quality", "TX-16": "blocked_source"},
            "summaries": {"SM-04": "blocked_source", "SM-08": "incomplete", "SM-09": "low_quality"},
        })

    def test_duplicates(self):
        self.assertEqual({name: ds["duplicates"] for name, ds in self.report.items()}, {
            "intent": {"IN-03": "IN-11"},
            "toxicity": {"TX-13": "TX-09"},
            "summaries": {"SM-11": "SM-01"},
        })


if __name__ == "__main__":
    unittest.main()
