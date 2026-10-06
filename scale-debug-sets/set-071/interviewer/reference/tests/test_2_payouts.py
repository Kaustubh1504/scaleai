import unittest

from payrun.reports import build_report

SETTLED = {
    "C01": (3798, 3798, 0), "C02": (1145, 0, 1145), "C03": (1250, 0, 1250),
    "C04": (338, 0, 338), "C06": (2636, 2636, 0), "C07": (1475, 0, 1475),
    "C08": (501, 0, 501), "C09": (855, 0, 855), "C10": (2075, 2075, 0),
    "C12": (3656, 3656, 0),
}


class TestPayouts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_settlement(self):
        self.maxDiff = None
        got = {cid: (r["gross"], r["paid"], r["carry_forward"]) for cid, r in self.report["statements"].items()}
        self.assertEqual(got, SETTLED)

    def test_paid_and_held(self):
        summary = self.report["summary"]
        self.assertEqual(summary["paid_contributors"], ["C01", "C06", "C10", "C12"])
        self.assertEqual(summary["held"], ["C02", "C03", "C04", "C07", "C08", "C09"])

    def test_total_paid(self):
        self.assertEqual(self.report["summary"]["total_paid"], 12165)


if __name__ == "__main__":
    unittest.main()
