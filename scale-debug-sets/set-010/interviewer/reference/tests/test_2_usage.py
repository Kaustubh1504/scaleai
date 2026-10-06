import unittest

from meterbill.report import build_report


class TestUsage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.usage = build_report()["usage"]

    def test_monthly_tokens(self):
        self.assertEqual(self.usage["monthly_tokens"], {
            "acme": 212300, "globex": 1240000, "hooli": 1500000, "initech": 30000,
            "soylent": 900000, "stark": 260000, "tyrell": 205000, "umbrella": 1080000,
            "wayne": 58000, "wonka": 150000,
        })

    def test_by_endpoint(self):
        self.maxDiff = None
        self.assertEqual(self.usage["by_endpoint"], {
            "acme": {"chat": 150000, "embed": 62300},
            "globex": {"chat": 900000, "embed": 340000},
            "hooli": {"chat": 1200000, "embed": 300000},
            "initech": {"chat": 30000},
            "soylent": {"chat": 500000, "embed": 400000},
            "stark": {"chat": 260000},
            "tyrell": {"chat": 205000},
            "umbrella": {"chat": 1000000, "embed": 80000},
            "wayne": {"chat": 40000, "embed": 18000},
            "wonka": {"embed": 150000},
        })


if __name__ == "__main__":
    unittest.main()
