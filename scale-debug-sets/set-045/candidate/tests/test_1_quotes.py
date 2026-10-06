import unittest

from cachekit.report import build_report

HITS = {"R02", "R06", "R08", "R09", "R16", "R17", "R20", "R21", "R24", "R25"}

PRICES = {
    "R01": 0.45, "R02": 0.5, "R03": 0.44, "R04": 2.2, "R05": 1.8, "R06": 0.4, "R07": 0.05,
    "R08": 0.45, "R09": 0.05, "R10": 1.6, "R11": 0.05, "R12": 0.09, "R13": 0.09, "R14": 1.76,
    "R15": 0.6, "R16": 0.495, "R17": 2.2, "R18": 1.6, "R19": 0.054, "R20": 0.06, "R21": 0.48,
    "R22": 2.16, "R23": 0.55, "R24": 0.48, "R25": 0.54, "R26": 0.6,
}


class TestQuotes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.requests = build_report()["requests"]

    def test_every_request_served(self):
        self.assertEqual(sorted(self.requests), sorted(PRICES))

    def test_hits(self):
        self.assertEqual(sorted(r for r, v in self.requests.items() if v["hit"]), sorted(HITS))

    def test_prices(self):
        self.maxDiff = None
        self.assertEqual({r: v["price"] for r, v in self.requests.items()}, PRICES)


if __name__ == "__main__":
    unittest.main()
