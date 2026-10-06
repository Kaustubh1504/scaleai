import unittest

from lbreplay.report import build_report

EXPECTED = {
    "R01": "b01", "R02": "b02", "R03": "b03", "R04": "b01", "R05": "b04",
    "R06": "b01", "R07": "b01", "R08": "b02", "R09": "b02", "R10": "b01",
    "R11": "b02", "R12": "b01", "R13": "b01", "R14": "b04", "R15": "b01",
    "R16": "b02", "R17": "b04", "R18": "b02", "R19": "b04", "R20": "b01",
    "R21": "b01", "R22": "b02", "R23": "b01", "R24": "b01", "R25": "b02",
    "R26": "b01", "R27": "b02", "R28": "b01", "R29": "b02", "R30": "b04",
}


class TestRouting(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()
        cls.assignments = cls.report["assignments"]

    def test_every_request_routed(self):
        self.assertEqual(sorted(self.assignments), sorted(EXPECTED))
        self.assertNotIn(None, self.assignments.values())

    def test_opening_requests(self):
        opening = {rid: self.assignments[rid] for rid in ("R01", "R02", "R03", "R04", "R05")}
        self.assertEqual(opening, {"R01": "b01", "R02": "b02", "R03": "b03", "R04": "b01", "R05": "b04"})

    def test_assignments(self):
        self.maxDiff = None
        self.assertEqual(self.assignments, EXPECTED)

    def test_sessions(self):
        self.assertEqual(self.report["sessions"],
                         {"alice": "b01", "bob": "b02", "carol": "b01", "dave": "b04", "erin": "b02"})


if __name__ == "__main__":
    unittest.main()
