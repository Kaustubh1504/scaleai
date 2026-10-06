import unittest

from seatbook.report import build_report


class TestReport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_session_occupancy(self):
        self.assertEqual({sid: (r["taken"], r["fill"]) for sid, r in self.report["sessions"].items()}, {
            "WS-01": (3, 0.75), "WS-02": (1, 0.33), "WS-03": (2, 0.4), "WS-04": (2, 1.0),
            "WS-05": (2, 0.33), "WS-06": (3, 1.0), "WS-07": (3, 0.5), "WS-08": (0, 0.0),
            "WS-09": (2, 1.0), "WS-10": (1, 0.1),
        })
        self.assertEqual(self.report["full_sessions"], ["WS-04", "WS-06", "WS-09"])

    def test_attendee_seats(self):
        self.assertEqual(self.report["attendees"], {
            "ana@lab.io": 5, "ben@lab.io": 2, "cara@lab.io": 1, "eli@lab.io": 1,
            "fay@lab.io": 2, "hana@lab.io": 2, "kim@lab.io": 3, "mo@lab.io": 3,
        })


if __name__ == "__main__":
    unittest.main()
