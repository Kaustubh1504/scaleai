import unittest

from crewplan.reports import build_report


class TestCourseCoverage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_courses_listed(self):
        self.assertEqual(list(self.report["courses"]), ["CODE-300", "LANG-ES", "MED-200", "QA-101"])

    def test_course_holders(self):
        holders = {course: row["holders"] for course, row in self.report["courses"].items()}
        self.assertEqual(holders, {"CODE-300": 4, "LANG-ES": 3, "MED-200": 6, "QA-101": 9})

    def test_most_demanded(self):
        self.assertEqual(self.report["most_demanded"], "QA-101")


if __name__ == "__main__":
    unittest.main()
