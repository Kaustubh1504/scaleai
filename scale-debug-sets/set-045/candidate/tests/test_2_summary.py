import unittest

from cachekit.report import build_report


class TestSummary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_origin_calls(self):
        self.assertEqual(self.report["origin_calls"], 16)

    def test_tenants(self):
        self.assertEqual(self.report["tenants"], {
            "acme": {"requests": 9, "hits": 3, "spend": 6.129},
            "globex": {"requests": 10, "hits": 4, "spend": 6.86},
            "initech": {"requests": 7, "hits": 3, "spend": 6.76},
        })

    def test_stale_served(self):
        self.assertEqual(self.report["stale_served"], ["R08", "R17"])


if __name__ == "__main__":
    unittest.main()
