import unittest

from refwatch.report import build_report


class TestReport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()
        cls.rows = cls.report["referrers"]
        cls.summary = cls.report["summary"]

    def test_referral_counts(self):
        got = {r: (row["referred"], row["qualifying"], row["self_referrals"]) for r, row in self.rows.items()}
        self.assertEqual(got, {
            "acc-01": (3, 2, 0), "acc-02": (2, 2, 0), "acc-03": (3, 2, 1),
            "acc-04": (3, 2, 0), "acc-05": (3, 2, 0), "acc-06": (1, 1, 1),
        })

    def test_2_flags(self):
        got = {r: row["flags"] for r, row in self.rows.items()}
        self.assertEqual(got, {
            "acc-01": [], "acc-02": [], "acc-03": ["self_referral"],
            "acc-04": ["burst"], "acc-05": [], "acc-06": ["self_referral"],
        })

    def test_3_payouts(self):
        got = {r: row["payout_usd"] for r, row in self.rows.items()}
        self.assertEqual(got, {
            "acc-01": 50, "acc-02": 50, "acc-03": 25,
            "acc-04": 50, "acc-05": 50, "acc-06": 0,
        })

    def test_held_referrers(self):
        self.assertEqual(self.summary["held"], ["acc-03", "acc-04", "acc-06"])

    def test_releasable_total(self):
        self.assertEqual(self.summary["releasable_usd"], 150)

    def test_top_referrer(self):
        self.assertEqual(self.summary["top_referrer"], "acc-01")


if __name__ == "__main__":
    unittest.main()
