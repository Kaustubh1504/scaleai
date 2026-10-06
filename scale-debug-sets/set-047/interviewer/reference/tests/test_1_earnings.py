import unittest

from paycycle.statement import build_statement


class TestEarnings(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lines = build_statement()["lines"]

    def test_ids_normalised(self):
        self.assertTrue(all(cid == cid.strip().upper() for cid in self.lines))
        self.assertIn("C-04", self.lines)

    def test_1_base_earnings(self):
        got = {cid: self.lines[cid]["base_cents"] for cid in
               ("C-01", "C-02", "C-03", "C-04", "C-05", "C-06", "C-07")}
        self.assertEqual(got, {"C-01": 650, "C-02": 295, "C-03": 1060, "C-04": 325,
                               "C-05": 1220, "C-06": 1425, "C-07": 220})

    def test_2_bonuses(self):
        got = {cid: line["bonus_cents"] for cid, line in self.lines.items()}
        self.assertEqual(got, {"C-01": 1725, "C-02": 2675, "C-03": 0, "C-04": 0, "C-05": 0,
                               "C-06": 1000, "C-07": 750, "C-08": 3000, "C-09": 400})


if __name__ == "__main__":
    unittest.main()
