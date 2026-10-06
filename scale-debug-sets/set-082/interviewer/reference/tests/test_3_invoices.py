import unittest

from meterbill.reports import build_report


class TestInvoices(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()
        cls.invoices = cls.report["invoices"]

    def test_usage_by_month(self):
        self.assertEqual({k: v["usage_units"] for k, v in self.invoices.items()}, {
            "acme/2026-03": 26000, "borealis/2026-03": 12300, "cinder/2026-02": 21500,
            "cinder/2026-03": 75400, "dunmore/2026-03": 300, "garnet/2026-03": 6000,
            "halcyon/2026-03": 2000,
        })

    def test_subtotals(self):
        self.assertEqual({k: v["subtotal_cents"] for k, v in self.invoices.items()}, {
            "acme/2026-03": 5050, "borealis/2026-03": 2220, "cinder/2026-02": 4950,
            "cinder/2026-03": 6258, "dunmore/2026-03": 1900, "garnet/2026-03": 4900,
            "halcyon/2026-03": 1900,
        })

    def test_discounted_total(self):
        self.assertEqual(self.invoices["acme/2026-03"]["total_cents"], 4293)

    def test_credits(self):
        self.assertEqual({k: v["credits_cents"] for k, v in self.invoices.items() if v["credits_cents"]}, {
            "acme/2026-03": 1350, "cinder/2026-02": 500, "dunmore/2026-03": 99,
            "garnet/2026-03": 725, "halcyon/2026-03": 1900,
        })
        self.assertEqual(self.report["unapplied_credits"], ["cr-03", "cr-05", "cr-06"])


if __name__ == "__main__":
    unittest.main()
