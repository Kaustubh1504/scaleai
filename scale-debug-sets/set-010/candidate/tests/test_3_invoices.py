import unittest

from meterbill.report import build_report


class TestInvoices(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        report = build_report()
        cls.invoices = report["invoices"]
        cls.top = report["top_tenants"]

    def test_base_fees(self):
        got = {t: (inv["plan"], inv["base"]) for t, inv in self.invoices.items()}
        self.assertEqual(got, {
            "acme": ("pro", 49.0), "globex": ("enterprise", 299.0), "hooli": ("enterprise", 299.0),
            "initech": ("free", 0.0), "soylent": ("enterprise", 299.0), "stark": ("pro", 49.0),
            "tyrell": ("pro", 49.0), "umbrella": ("enterprise", 299.0), "wayne": ("free", 0.0),
            "wonka": ("pro", 49.0),
        })

    def test_overage(self):
        got = {t: inv["overage"] for t, inv in self.invoices.items()}
        self.assertEqual(got, {
            "acme": 5.2, "globex": 60.0, "hooli": 125.0, "initech": 0.0, "soylent": 0.0,
            "stark": 24.0, "tyrell": 2.0, "umbrella": 20.0, "wayne": 4.0, "wonka": 0.0,
        })

    def test_discounts(self):
        got = {t: inv["discount"] for t, inv in self.invoices.items()}
        self.assertEqual(got, {
            "acme": 0.0, "globex": 35.9, "hooli": 21.2, "initech": 0.0, "soylent": 14.95,
            "stark": 10.95, "tyrell": 0.0, "umbrella": 0.0, "wayne": 0.0, "wonka": 0.0,
        })

    def test_top_tenants(self):
        self.assertEqual(self.top, ["hooli", "globex", "umbrella"])


if __name__ == "__main__":
    unittest.main()
