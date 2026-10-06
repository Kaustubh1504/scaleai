import unittest

from seatbook.reports import build_report


class TestReport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()
        cls.summary = cls.report["summary"]

    def test_sales(self):
        self.assertEqual(
            (self.summary["sold"], self.summary["revenue"], self.summary["sold_by_section"]),
            (17, 1790, {"BALC": 2, "ORCH": 15}),
        )

    def test_confirm_and_release_outcomes(self):
        statuses, actions = self.report["statuses"], self.report["actions"]
        picked = {rid: st for rid, st in statuses.items() if actions[rid] in ("confirm", "release", "cancel")}
        self.assertEqual(picked, {
            "R03": "confirmed", "R05": "no_hold", "R06": "confirmed", "R10": "released",
            "R11": "confirmed", "R12": "noop", "R15": "confirmed", "R18": "confirmed",
            "R21": "no_hold",
        })

    def test_ignored_requests(self):
        self.assertEqual(self.summary["ignored"], ["R08", "R20"])


if __name__ == "__main__":
    unittest.main()
