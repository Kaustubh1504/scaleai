import unittest

from lbsim.reports import build_report


class TestBackends(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.backends = build_report()["backends"]

    def test_served(self):
        self.assertEqual({k: v["served"] for k, v in self.backends.items()}, {
            "api-1": 6, "api-2": 5, "api-3": 3, "api-4": 0,
            "bt-1": 4, "bt-2": 0, "bt-3": 3,
            "st-1": 3, "st-2": 2, "st-3": 0,
        })

    def test_peak_connections(self):
        self.assertEqual({k: v["peak"] for k, v in self.backends.items() if v["served"]}, {
            "api-1": 3, "api-2": 2, "api-3": 1, "bt-1": 2, "bt-3": 1, "st-1": 1, "st-2": 1,
        })

    def test_busy_ms(self):
        self.assertEqual({k: v["busy_ms"] for k, v in self.backends.items() if v["served"]}, {
            "api-1": 3350, "api-2": 1650, "api-3": 1000, "bt-1": 2450, "bt-3": 1000, "st-1": 2050, "st-2": 400,
        })


if __name__ == "__main__":
    unittest.main()
