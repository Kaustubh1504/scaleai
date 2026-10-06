import unittest

from payrun.reports import build_report

EARNED = {
    "C01": (3, 2298), "C02": (2, 1205), "C03": (1, 750), "C04": (2, 2088), "C06": (3, 1436),
    "C07": (1, 750), "C08": (1, 576), "C09": (2, 1155), "C10": (1, 75), "C12": (2, 1656),
}
ADJUSTMENTS = {
    "C01": (1500, 0), "C02": (0, 410), "C03": (500, 0), "C04": (0, 1250), "C06": (0, 0),
    "C07": (725, 0), "C08": (0, 75), "C09": (0, 300), "C10": (100, 0), "C12": (2000, 0),
}


class TestStatements(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()
        cls.rows = cls.report["statements"]

    def test_active_contributors_only(self):
        self.assertEqual(sorted(self.rows), sorted(EARNED))

    def test_lines_and_earned(self):
        got = {cid: (r["lines"], r["earned"]) for cid, r in self.rows.items()}
        self.assertEqual(got, EARNED)

    def test_adjustments(self):
        got = {cid: (r["bonus"], r["clawback"]) for cid, r in self.rows.items()}
        self.assertEqual(got, ADJUSTMENTS)

    def test_unmatched_adjustments(self):
        self.assertEqual(self.report["summary"]["unmatched_adjustments"], 1)


if __name__ == "__main__":
    unittest.main()
