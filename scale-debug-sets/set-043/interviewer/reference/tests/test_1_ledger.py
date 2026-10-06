import unittest

from seatbook.report import build_report


class TestLedgerOutcomes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.outcomes = build_report()["outcomes"]

    def pick(self, *ids):
        return {i: self.outcomes.get(i) for i in ids}

    def test_bookings_and_comps(self):
        ids = ["E01", "E02", "E08", "E10", "E11", "E12", "E13", "E14", "E16", "E19", "E21", "E23",
               "E25", "E26", "E27", "E28", "E29", "E30", "E31", "E32", "E33"]
        self.assertEqual(self.pick(*ids), {i: "ok" for i in ids})

    def test_hold_expiry(self):
        self.assertEqual(self.pick("E04", "E05", "E06", "E07", "E35", "E36"), {
            "E04": "ok", "E05": "expired", "E06": "ok", "E07": "ok",
            "E35": "expired", "E36": "nothing_to_cancel",
        })

    def test_rejection_reasons(self):
        self.assertEqual(self.pick("E03", "E09", "E15", "E17", "E18", "E20", "E22", "E24", "E34"), {
            "E03": "full", "E09": "full", "E15": "full", "E17": "full", "E18": "unknown_session",
            "E20": "duplicate", "E22": "no_hold", "E24": "closed", "E34": "full",
        })


if __name__ == "__main__":
    unittest.main()
