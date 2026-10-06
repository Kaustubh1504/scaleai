import unittest

from seatplan.reports import build_report


class TestAssignment(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.assignments = build_report()["assignments"]

    def test_only_open_projects_staffed(self):
        self.assertEqual(sorted(self.assignments),
                         ["PR-01", "PR-02", "PR-03", "PR-04", "PR-05", "PR-06", "PR-08"])

    def test_americas_projects(self):
        got = {pid: self.assignments[pid] for pid in ("PR-04", "PR-05", "PR-06", "PR-08")}
        self.assertEqual(got, {"PR-04": ["A-03", "A-01"], "PR-05": ["A-02", "A-05"],
                               "PR-06": ["A-02"], "PR-08": []})

    def test_1_emea_projects(self):
        got = {pid: self.assignments[pid] for pid in ("PR-01", "PR-02")}
        self.assertEqual(got, {"PR-01": ["E-01", "E-02"], "PR-02": ["E-01", "E-02"]})

    def test_2_apac_projects(self):
        self.assertEqual(self.assignments["PR-03"], ["P-01", "P-02"])


if __name__ == "__main__":
    unittest.main()
