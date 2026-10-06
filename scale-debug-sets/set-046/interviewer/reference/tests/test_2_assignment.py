import unittest
from datetime import datetime

from routedesk.reports import build_report


class TestAssignment(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_inactive_reviewers_get_nothing(self):
        self.assertNotIn("r-02", self.report["assignments"])
        self.assertNotIn("r-08", self.report["assignments"])

    def test_3_english_reviewers(self):
        got = {rid: self.report["assignments"][rid] for rid in ("r-01", "r-03", "r-06")}
        self.assertEqual(got, {"r-01": ["P-02", "P-04"], "r-03": ["P-26"], "r-06": ["P-11", "P-14"]})

    def test_4_german_reviewers(self):
        got = {rid: self.report["assignments"][rid] for rid in ("r-05", "r-07")}
        self.assertEqual(got, {"r-05": ["P-10", "P-16", "P-17"], "r-07": []})

    def test_sla_due_times(self):
        sla = self.report["sla"]
        self.assertEqual(sla["P-02"], datetime(2026, 3, 2, 11, 5))
        self.assertEqual(sla["P-13"], datetime(2026, 3, 2, 17, 20))
        self.assertEqual(sla["P-15"], datetime(2026, 3, 3, 9, 35))


if __name__ == "__main__":
    unittest.main()
