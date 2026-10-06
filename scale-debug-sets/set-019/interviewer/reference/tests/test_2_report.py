import unittest

from boxoffice.reports import build_report


class TestReport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_rejections(self):
        self.assertEqual(self.report["rejections"],
                         {"no_hold": 3, "seat_held": 1, "sold": 1, "unknown_seat": 1})

    def test_revenue(self):
        self.assertEqual(self.report["revenue"], 627.0)

    def test_occupancy(self):
        self.assertEqual(self.report["occupancy_pct"], 50.0)


if __name__ == "__main__":
    unittest.main()
