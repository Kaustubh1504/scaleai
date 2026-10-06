import unittest

from seatplan.reports import build_report


class TestReport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_americas_unfilled(self):
        got = {pid: self.report["unfilled"][pid] for pid in ("PR-04", "PR-05", "PR-06", "PR-08")}
        self.assertEqual(got, {"PR-04": 0, "PR-05": 0, "PR-06": 0, "PR-08": 1})

    def test_americas_utilisation(self):
        got = {cid: self.report["utilisation"][cid] for cid in ("A-01", "A-02", "A-03", "A-05")}
        self.assertEqual(got, {"A-01": 0.33, "A-02": 0.75, "A-03": 1.0, "A-05": 0.5})

    def test_3_skill_gaps_for_americas_skills(self):
        gaps = self.report["skill_gaps"]
        self.assertEqual({"math": gaps.get("math"), "spanish": gaps.get("spanish")},
                         {"math": 1, "spanish": 0})


if __name__ == "__main__":
    unittest.main()
