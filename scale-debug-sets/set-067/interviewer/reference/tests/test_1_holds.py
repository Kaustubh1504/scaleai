import unittest

from seatbook.reports import build_report


class TestHolds(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()
        cls.held = cls.report["held_seats"]

    def test_orchestra_holds(self):
        self.maxDiff = None
        orch = {rid: seats for rid, seats in self.held.items() if seats[0].startswith("ORCH")}
        self.assertEqual(orch, {
            "R01": ["ORCH-A1", "ORCH-A2", "ORCH-A3", "ORCH-A4"],
            "R02": ["ORCH-A5", "ORCH-A6", "ORCH-A7", "ORCH-A8"],
            "R04": ["ORCH-A9", "ORCH-A10", "ORCH-A11"],
            "R07": ["ORCH-A5", "ORCH-A6", "ORCH-A7", "ORCH-A8", "ORCH-A12"],
            "R13": ["ORCH-B1", "ORCH-B2", "ORCH-B3"],
        })

    def test_balcony_holds(self):
        balc = {rid: seats for rid, seats in self.held.items() if seats[0].startswith("BALC")}
        self.assertEqual(balc, {
            "R09": ["BALC-A1", "BALC-A2", "BALC-A3"],
            "R16": ["BALC-A1", "BALC-A2"],
            "R17": ["BALC-A1", "BALC-A2"],
            "R22": ["BALC-A3", "BALC-A4"],
        })

    def test_hold_outcomes(self):
        statuses, actions = self.report["statuses"], self.report["actions"]
        holds = {rid: st for rid, st in statuses.items() if actions[rid] == "hold"}
        self.assertEqual(holds, {
            "R01": "held", "R02": "held", "R04": "held", "R07": "held", "R09": "held",
            "R13": "held", "R14": "duplicate", "R16": "held", "R17": "held",
            "R19": "rejected", "R22": "held",
        })


if __name__ == "__main__":
    unittest.main()
