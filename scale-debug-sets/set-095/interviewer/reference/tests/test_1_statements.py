import unittest

from paycalc.payfile import build_report

ROSTER = ["C-01", "C-02", "C-03", "C-04", "C-05", "C-06", "C-07", "C-08", "C-09", "C-10"]

TASKS_AND_GROSS = {
    "C-01": (5, "7.50"),
    "C-02": (3, "9.00"),
    "C-03": (5, "5.70"),
    "C-04": (3, "6.46"),
    "C-05": (5, "5.19"),
    "C-06": (3, "1.37"),
    "C-07": (5, "9.00"),
    "C-08": (2, "1.00"),
    "C-09": (4, "7.20"),
    "C-10": (0, "0.00"),
}

ADJUSTMENTS_AND_NET = {
    "C-01": ("-1.20", "6.30"),
    "C-02": ("5.00", "14.00"),
    "C-03": ("0.25", "5.95"),
    "C-04": ("-0.60", "5.86"),
    "C-05": ("0.00", "5.19"),
    "C-06": ("2.50", "3.87"),
    "C-07": ("1000.00", "1009.00"),
    "C-08": ("9.00", "10.00"),
    "C-09": ("3.00", "10.20"),
    "C-10": ("3.00", "3.00"),
}


class TestStatements(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.statements = build_report()["statements"]

    def test_every_roster_contributor_has_a_statement(self):
        self.assertEqual(sorted(self.statements), ROSTER)

    def test_tasks_and_gross(self):
        got = {cid: (s["tasks"], s["gross"]) for cid, s in self.statements.items()}
        self.assertEqual(got, TASKS_AND_GROSS)

    def test_1_adjustments_and_net(self):
        self.maxDiff = None
        got = {cid: (s["adjustments"], s["net"]) for cid, s in self.statements.items()}
        self.assertEqual(got, ADJUSTMENTS_AND_NET)

    def test_held_contributors(self):
        held = sorted(cid for cid, s in self.statements.items() if s["status"] == "held")
        self.assertEqual(held, ["C-01", "C-03", "C-04", "C-05", "C-06", "C-10"])


if __name__ == "__main__":
    unittest.main()
