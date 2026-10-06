import unittest

from paycycle.statement import build_statement


class TestStatement(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.statement = build_statement()

    def test_small_balance_carried_over(self):
        line = self.statement["lines"]["C-04"]
        self.assertEqual((line["net_cents"], line["status"]), (317, "carried_over"))
        self.assertIn("C-04", self.statement["carried_over"])

    def test_3_fees_on_task_only_earners(self):
        got = {cid: (self.statement["lines"][cid]["fee_cents"], self.statement["lines"][cid]["net_cents"])
               for cid in ("C-03", "C-04", "C-05")}
        self.assertEqual(got, {"C-03": (27, 1033), "C-04": (8, 317), "C-05": (31, 1189)})


if __name__ == "__main__":
    unittest.main()
