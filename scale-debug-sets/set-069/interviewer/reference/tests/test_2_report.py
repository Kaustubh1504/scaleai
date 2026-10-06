import unittest

from guidecache.reports import build_report

BASE = ["positive", "negative", "neutral"]


class TestReport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_sentiment_payloads(self):
        self.maxDiff = None
        payloads = {rid: labels for rid, labels in self.report["payloads"].items() if rid.startswith("S")}
        self.assertEqual(payloads, {
            "S1": BASE + ["sarcasm"], "S2": BASE, "S3": BASE + ["sarcasm"],
            "S4": BASE, "S5": BASE + ["sarcasm"], "S6": BASE,
        })

    def test_not_found_payloads(self):
        self.assertEqual((self.report["payloads"]["X1"], self.report["payloads"]["X2"]), (None, None))


if __name__ == "__main__":
    unittest.main()
