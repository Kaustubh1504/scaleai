import unittest

from meterbill.report import build_report


class TestThrottle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.throttle = build_report()["throttle"]

    def test_throttled_requests(self):
        self.assertEqual(self.throttle["throttled"], ["R07", "R11", "R17", "R18", "R21", "R22"])

    def test_retry_after(self):
        got = {rid: self.throttle["retry_after_s"][rid] for rid in ("R07", "R11", "R17", "R22")}
        self.assertEqual(got, {"R07": 35.0, "R11": 52.0, "R17": 55.0, "R22": 0.001})

    def test_requests_under_limit_pass(self):
        got = {rid for rid in self.throttle["retry_after_s"] if rid in ("R01", "R02", "R12", "R19", "R20")}
        self.assertEqual(got, set())


if __name__ == "__main__":
    unittest.main()
