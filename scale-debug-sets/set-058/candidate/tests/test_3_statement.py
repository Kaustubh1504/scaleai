import unittest

from meterbill.reports import build_report


class TestStatement(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.statement = build_report()["statement"]

    def test_top_tenants(self):
        self.assertEqual(self.statement["top_tenants"], [["orbit", 6], ["brightpath", 5], ["kestrel", 5]])

    def test_plan_mix(self):
        self.assertEqual(self.statement["plan_mix"], {"enterprise": 2, "free": 3, "pro": 5})


if __name__ == "__main__":
    unittest.main()
