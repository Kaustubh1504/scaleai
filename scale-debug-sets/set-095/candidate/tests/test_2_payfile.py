import unittest

from paycalc.payfile import build_report


class TestPayfile(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_2_audit_flags(self):
        self.assertEqual(self.report["flags"], {"C-02": ["fast:helix"], "C-05": ["fast:ember"]})

    def test_3_payout_file(self):
        self.assertEqual(self.report["payout_file"], [
            "830,ach,10.00",
            "61005,paypal,1009.00",
            "104433,wire,14.00",
            "230111,paypal,10.20",
        ])

    def test_summary(self):
        self.assertEqual(self.report["summary"], {
            "paid": 4,
            "held": 6,
            "totals_by_method": {"ach": "10.00", "paypal": "1019.20", "wire": "14.00"},
        })


if __name__ == "__main__":
    unittest.main()
