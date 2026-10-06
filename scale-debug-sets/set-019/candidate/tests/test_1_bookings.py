import unittest

from boxoffice.reports import build_report

EXPECTED_SOLD = {
    "A1": "C01", "A2": "C02", "A3": "C12", "A4": "C12", "A6": "C02",
    "B1": "C03", "B2": "C06", "B3": "C05", "C1": "C08", "C2": "C11",
}


class TestBookings(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_first_hold_wins_simultaneous_requests(self):
        self.assertEqual(self.report["sold"].get("A1"), "C01")

    def test_expired_hold_frees_the_seat(self):
        self.assertEqual(self.report["sold"].get("B2"), "C06")

    def test_sold_seats(self):
        self.maxDiff = None
        self.assertEqual(self.report["sold"], EXPECTED_SOLD)

    def test_by_customer(self):
        self.assertEqual(self.report["by_customer"], {
            "C01": ["A1"], "C02": ["A2", "A6"], "C03": ["B1"], "C05": ["B3"],
            "C06": ["B2"], "C08": ["C1"], "C11": ["C2"], "C12": ["A3", "A4"],
        })


if __name__ == "__main__":
    unittest.main()
