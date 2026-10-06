import unittest

from leasehold.reports import build_report


class TestReport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_dead_letter(self):
        self.assertEqual(self.report["dead_letter"], ["K05", "K07"])

    def test_attempts(self):
        self.assertEqual(self.report["attempts"], {
            "K01": 1, "K02": 1, "K03": 1, "K04": 1, "K05": 1, "K06": 2,
            "K07": 3, "K08": 1, "K09": 1, "K10": 1, "K11": 1, "K12": 2,
        })

    def test_mean_ack_seconds(self):
        self.assertEqual(self.report["mean_ack_seconds"], {"audio": 336.7, "ocr": 136.7, "review": 160.0})


if __name__ == "__main__":
    unittest.main()
