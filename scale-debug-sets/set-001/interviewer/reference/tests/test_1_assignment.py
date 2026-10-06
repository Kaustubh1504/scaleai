import unittest

from staffing.reports import build_report

EXPECTED_ASSIGNMENTS = {
    "P01": ["C01", "C15"],
    "P02": ["C06", "C07"],
    "P03": ["C03", "C10"],
    "P04": ["C13", "C09"],
    "P05": [],
    "P06": ["C05", "C14", "C11"],
    "P07": ["C02"],
    "P08": ["C16"],
    "P09": [],
    "P10": [],
}


class TestAssignment(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_highest_priority_project_staffed_first(self):
        self.assertEqual(self.report["assignments"]["P02"], ["C06", "C07"])

    def test_paused_project_gets_nobody(self):
        self.assertEqual(self.report["assignments"]["P05"], [])

    def test_full_assignment_table(self):
        self.maxDiff = None
        self.assertEqual(self.report["assignments"], EXPECTED_ASSIGNMENTS)


if __name__ == "__main__":
    unittest.main()
