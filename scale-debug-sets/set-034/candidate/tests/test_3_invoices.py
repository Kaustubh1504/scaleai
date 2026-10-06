import unittest

from meterbill.reports import build_report


class TestInvoices(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_overage_tokens(self):
        got = {t: inv["overage_tokens"] for t, inv in self.report["invoices"].items()}
        self.assertEqual(got, {
            "t-acme": 800, "t-bolt": 9700, "t-cove": 700, "t-dune": 10000, "t-echo": 0,
            "t-fern": 1400, "t-gale": 11700, "t-hive": 0, "t-iris": 0, "t-jade": 1000,
        })

    def test_invoice_amounts(self):
        got = {t: inv["amount"] for t, inv in self.report["invoices"].items()}
        self.assertEqual(got, {
            "t-acme": "0.32", "t-bolt": "2.43", "t-cove": "0.28", "t-dune": "1.50", "t-echo": "0.00",
            "t-fern": "0.56", "t-gale": "2.93", "t-hive": "0.00", "t-iris": "0.00", "t-jade": "0.25",
        })

    def test_total_and_top_tenants(self):
        self.assertEqual(self.report["total"], "8.27")
        self.assertEqual(self.report["top_tenants"], ["t-gale", "t-bolt", "t-dune"])


if __name__ == "__main__":
    unittest.main()
