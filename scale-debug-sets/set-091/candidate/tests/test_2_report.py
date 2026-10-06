import unittest

from seatbook.reports import build_report


class TestSummary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.summary = build_report()["summary"]

    def test_seats_left(self):
        self.assertEqual(self.summary["seats_left"], {
            "A1": 2, "A2": 0, "B1": 0, "B2": 0, "C1": 0,
            "C2": 1, "D1": 7, "D2": 0, "E1": 2, "E2": 1,
        })

    def test_totals(self):
        self.assertEqual((self.summary["total_booked"], self.summary["fill_rate"]), (35, 0.729))

    def test_top_member(self):
        self.assertEqual(self.summary["top_member"], "m-01")


if __name__ == "__main__":
    unittest.main()
