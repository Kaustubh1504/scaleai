import unittest

from meterbill.reports import build_report


class TestInvoices(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.invoices = build_report()["invoices"]

    def test_credit_applied(self):
        self.assertEqual(self.invoices["delta-labs"], {
            "plan": "pro", "units": 1400, "gross_cents": 3000, "credit_cents": 1500, "amount_cents": 1500,
        })

    def test_overage_part_cents(self):
        self.assertEqual(self.invoices["harbor"], {
            "plan": "pro", "units": 2203, "gross_cents": 3201, "credit_cents": 200, "amount_cents": 3001,
        })

    def test_amounts_due(self):
        amounts = {t: inv["amount_cents"] for t, inv in self.invoices.items() if t not in ("delta-labs", "harbor")}
        self.assertEqual(amounts, {
            "acorn": 0, "brightpath": 2900, "fjord": 0, "ivory": 50000,
            "kestrel": 2900, "orbit": 40000, "quill": 0, "sable": 2900,
        })

    def test_billed_units(self):
        self.assertEqual({t: self.invoices[t]["units"] for t in ("acorn", "brightpath", "fjord", "quill", "sable")},
                         {"acorn": 350, "brightpath": 400, "fjord": 180, "quill": 40, "sable": 100})


if __name__ == "__main__":
    unittest.main()
