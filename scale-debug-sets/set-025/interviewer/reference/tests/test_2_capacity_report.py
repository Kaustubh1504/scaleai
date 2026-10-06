import unittest

from crew.reports import build_report


class TestCapacityReport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_utilization(self):
        self.assertEqual(self.report["utilization"], {
            "C01": 1.0, "C02": 1.0, "C03": 1.0, "C04": 1.0, "C05": 0.56,
            "C08": 1.0, "C09": 1.0, "C10": 1.0, "C11": 0.0, "C12": 1.0,
        })

    def test_idle(self):
        self.assertEqual(self.report["idle"], ["C11"])


if __name__ == "__main__":
    unittest.main()
