import unittest

from revflow.reports import build_report


class TestReport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_queue(self):
        self.assertEqual(self.report["queue"], ["T-08", "T-09", "T-04", "T-05", "T-11"])

    def test_cycle_hours(self):
        self.assertEqual(self.report["cycle_hours"], {"T-01": 3.0, "T-02": 27.0, "T-03": 20.0})


if __name__ == "__main__":
    unittest.main()
