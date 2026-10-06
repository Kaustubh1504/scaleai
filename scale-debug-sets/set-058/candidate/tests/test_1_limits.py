import unittest

from meterbill.reports import build_report


class TestLimits(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.throttled = build_report()["throttled"]

    def test_enterprise_not_throttled(self):
        self.assertEqual(self.throttled["orbit"], [])

    def test_window_boundary(self):
        self.assertEqual(self.throttled["kestrel"], ["2026-05-01 10:01:05"])

    def test_suspended_tenant(self):
        self.assertEqual(self.throttled["ivory"],
                         ["2026-05-01 08:00:00", "2026-05-01 12:30:00", "2026-05-02 08:00:00"])

    def test_other_tenants(self):
        others = {t: v for t, v in self.throttled.items() if t not in ("orbit", "kestrel", "ivory")}
        self.assertEqual(others, {
            "acorn": ["2026-05-01 09:00:40"],
            "brightpath": ["2026-05-01 11:00:15"],
            "delta-labs": [],
            "fjord": [],
            "harbor": [],
            "quill": [],
            "sable": [],
        })


if __name__ == "__main__":
    unittest.main()
