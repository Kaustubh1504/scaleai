import unittest

from lbsim.reports import build_report


class TestReport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.summary = build_report()["summary"]

    def test_totals(self):
        self.assertEqual((self.summary["routed"], self.summary["rejected"], self.summary["reject_rate"]),
                         (26, 1, 0.037))

    def test_by_pool(self):
        self.assertEqual(self.summary["by_pool"], {"api": 14, "batch": 7, "static": 5})

    def test_utilization(self):
        self.assertEqual(self.summary["utilization"], {
            "api-1": 0.272, "api-2": 0.201, "api-3": 0.122,
            "bt-1": 0.199, "bt-3": 0.244, "st-1": 0.5, "st-2": 0.098,
        })


if __name__ == "__main__":
    unittest.main()
