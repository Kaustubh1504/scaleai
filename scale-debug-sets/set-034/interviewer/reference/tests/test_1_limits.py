import unittest

from meterbill.reports import build_report


class TestLimits(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_effective_limits(self):
        self.assertEqual(self.report["limits"], {
            "t-acme": 3, "t-bolt": 5, "t-cove": 2, "t-dune": 10, "t-echo": 0,
            "t-fern": 3, "t-gale": 4, "t-hive": 10, "t-iris": 3, "t-jade": 5,
        })

    def test_throttled_requests(self):
        self.maxDiff = None
        self.assertEqual(self.report["throttled"], {
            "t-acme": ["a05"], "t-bolt": [], "t-cove": ["c03"], "t-dune": [],
            "t-echo": ["e01", "e02"], "t-fern": ["f04", "f05"], "t-gale": ["g05"],
            "t-hive": [], "t-iris": [], "t-jade": [],
        })

    def test_unknown_tenant_ignored(self):
        self.assertNotIn("t-zed", self.report["usage"])


if __name__ == "__main__":
    unittest.main()
