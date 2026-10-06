import unittest

from payroll.reports import build_report


class TestPayoutReport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_held_balances(self):
        held = {cid: row["held_usd_cents"] for cid, row in self.report["contributors"].items()
                if row["held_usd_cents"]}
        self.assertEqual(held, {"C02": 675, "C12": 1035})

    def test_local_currency_payouts(self):
        local = {cid: (row["currency"], row["payout"])
                 for cid, row in self.report["contributors"].items() if row["currency"] != "USD"}
        self.assertEqual(local, {
            "C01": ("EUR", 879),
            "C04": ("INR", 116340),
            "C05": ("GBP", 995),
            "C07": ("EUR", 1932),
            "C09": ("GBP", 608),
            "C11": ("INR", 106368),
            "C12": ("EUR", 0),
        })

    def test_top_contributors(self):
        self.assertEqual(self.report["top_contributors"], [["C06", 4], ["C02", 3], ["C04", 3]])


if __name__ == "__main__":
    unittest.main()
