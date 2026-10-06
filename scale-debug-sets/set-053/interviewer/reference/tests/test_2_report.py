import unittest

from prelabelqa.reports import build_report


class TestReport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_added_boxes(self):
        self.assertEqual(self.report["added"], {"img-01": 1, "img-02": 1, "img-07": 1, "img-10": 1})

    def test_out_of_bounds(self):
        self.assertEqual(self.report["out_of_bounds"], [
            ["img-01", None, "sign"],
            ["img-09", "B15", "car"],
        ])


if __name__ == "__main__":
    unittest.main()
