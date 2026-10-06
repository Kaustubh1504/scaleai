import unittest

from hitlroute.reports import build_report


class TestWorklists(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()
        cls.worklists = cls.report["worklists"]

    def test_assignments_and_backlog(self):
        self.assertEqual(self.report["assignments"], {
            "T02": "r02", "T03": "r02", "T04": "r02", "T06": "r01", "T08": None, "T09": None, "T10": None,
            "P02": "r01", "P03": "r06", "P05": "r01", "P06": "r06", "P08": "r01",
            "C02": "r03", "C03": "r05", "C05": "r07", "C06": "r10", "C07": "r03", "C08": "r05", "C09": "r10",
        })
        self.assertEqual(self.report["backlog"], ["T08", "T09", "T10"])

    def test_single_priority_worklists(self):
        picked = {rid: self.worklists[rid] for rid in ("r02", "r03", "r06", "r07")}
        self.assertEqual(picked, {
            "r02": ["T04", "T02", "T03"], "r03": ["C02", "C07"], "r06": ["P06", "P03"], "r07": ["C05"],
        })

    def test_mixed_priority_worklists(self):
        picked = {rid: self.worklists[rid] for rid in ("r01", "r05")}
        self.assertEqual(picked, {"r01": ["T06", "P05", "P08", "P02"], "r05": ["C08", "C03"]})

    def test_equal_confidence_worklist(self):
        self.assertEqual(self.worklists["r10"], ["C09", "C06"])


if __name__ == "__main__":
    unittest.main()
