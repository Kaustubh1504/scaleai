import unittest

from meterbill.reports import build_report


class TestRateLimits(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_effective_limits(self):
        limits = self.report["limits"]
        self.assertEqual(limits["dunmore"], [2, 5])
        self.assertEqual(limits["kestrel"], [30, 60])
        self.assertEqual(limits["elm-labs"], [3, 10])
        self.assertEqual(limits["acme"], [10, 60])

    def test_rejected_requests(self):
        self.assertEqual(sorted(self.report["rejected"]), ["gw1-0005", "gw2-0005", "gw2-0006"])

    def test_retry_after_hints(self):
        dunmore = set(self.report["timeline"]["dunmore"])
        hints = {rid: v for rid, v in self.report["rejected"].items() if rid in dunmore}
        self.assertEqual(hints, {"gw2-0005": 1.75, "gw2-0006": 0.75})


if __name__ == "__main__":
    unittest.main()
