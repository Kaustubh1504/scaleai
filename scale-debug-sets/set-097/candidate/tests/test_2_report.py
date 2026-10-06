import unittest

from podstaff.reports import build_report


class TestReport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_open_seats(self):
        self.assertEqual(self.report["open_seats"], {"P07": 1})

    def test_course_demand(self):
        self.assertEqual(self.report["course_demand"],
                         {"audio-120": 1, "code-301": 1, "core-101": 4, "pii-110": 1, "safety-201": 1})
        self.assertEqual(self.report["top_course"], "core-101")

    def test_multi_project_contributors(self):
        self.assertEqual(self.report["multi_project"], {
            "C01": ["P01", "P02", "P03"],
            "C02": ["P01", "P03"],
            "C03": ["P01", "P05", "P09"],
            "C14": ["P06", "P10"],
            "C15": ["P07", "P10"],
        })


if __name__ == "__main__":
    unittest.main()
