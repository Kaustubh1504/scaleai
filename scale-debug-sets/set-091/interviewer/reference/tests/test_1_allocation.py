import unittest

from seatbook.reports import build_report


class TestAllocation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()
        cls.sessions = cls.report["sessions"]

    def test_every_session_reported(self):
        self.assertEqual(sorted(self.sessions),
                         ["A1", "A2", "B1", "B2", "C1", "C2", "D1", "D2", "E1", "E2"])

    def test_contested_sessions_follow_tier(self):
        contested = {sid: (self.sessions[sid]["booked"], self.sessions[sid]["waitlist"]) for sid in ("A2", "C2")}
        self.assertEqual(contested, {
            "A2": (["H04", "H06"], ["H05"]),
            "C2": (["H15"], ["H16"]),
        })

    def test_expired_holds(self):
        self.assertEqual(self.report["expired"], ["H03", "H10", "H17", "H23"])

    def test_booked_holds(self):
        booked = {sid: s["booked"] for sid, s in self.sessions.items() if sid not in ("A2", "C2")}
        self.assertEqual(booked, {
            "A1": ["H01", "H02"], "B1": ["H07", "H09"], "B2": [], "C1": ["H12", "H13"],
            "D1": ["H18"], "D2": ["H20"], "E1": ["H22"], "E2": ["H24", "H25"],
        })

    def test_seats_booked(self):
        seats = {sid: s["seats_booked"] for sid, s in self.sessions.items()}
        self.assertEqual(seats, {
            "A1": 6, "A2": 4, "B1": 5, "B2": 0, "C1": 6,
            "C2": 2, "D1": 3, "D2": 2, "E1": 2, "E2": 5,
        })

    def test_waitlists_of_uncontested_sessions(self):
        waiting = {sid: self.sessions[sid]["waitlist"] for sid in ("A1", "B2", "C1", "D1", "D2", "E1", "E2")}
        self.assertEqual(waiting, {
            "A1": [], "B2": ["H11"], "C1": [], "D1": [], "D2": ["H21"], "E1": [], "E2": [],
        })

    def test_unknown_member_and_blank_seats_ignored(self):
        seen = set(self.report["expired"])
        for s in self.sessions.values():
            seen.update(s["booked"], s["waitlist"])
        self.assertFalse({"H14", "H19"} & seen)


if __name__ == "__main__":
    unittest.main()
