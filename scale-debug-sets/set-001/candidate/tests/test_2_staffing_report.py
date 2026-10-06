import unittest

from staffing.reports import build_report


class TestStaffingReport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_course_gated_projects_fully_staffed(self):
        staffed = {pid: len(self.report["assignments"][pid]) for pid in ("P01", "P02", "P03")}
        self.assertEqual(staffed, {"P01": 2, "P02": 2, "P03": 2})

    def test_open_seats(self):
        self.assertEqual(self.report["open_seats"], {"P07": 1, "P09": 2, "P10": 1})

    def test_bench(self):
        self.assertEqual(self.report["bench"], ["C08"])


if __name__ == "__main__":
    unittest.main()
