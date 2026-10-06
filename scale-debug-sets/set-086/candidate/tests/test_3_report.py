import unittest

from lbreplay.report import build_report


class TestReport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.summary = build_report()["summary"]

    def test_request_counts(self):
        counts = {bid: row["requests"] for bid, row in self.summary["backends"].items()}
        self.assertEqual(counts, {"b01": 14, "b02": 10, "b03": 1, "b04": 5})

    def test_median_latency(self):
        p50 = {bid: row["p50_ms"] for bid, row in self.summary["backends"].items()}
        self.assertEqual(p50, {"b01": 300, "b02": 300, "b03": 2500, "b04": 350})

    def test_zones(self):
        self.assertEqual(self.summary["zones"], {"east": 24, "west": 6})

    def test_failovers_and_rejections(self):
        self.assertEqual((self.summary["failovers"], self.summary["rejected"]), (1, []))


if __name__ == "__main__":
    unittest.main()
