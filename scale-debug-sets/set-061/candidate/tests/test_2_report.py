import unittest

from tripwire.report import build_report


class TestReport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()
        cls.summary = cls.report["summary"]

    def test_flags_per_annotator(self):
        got = {a: r["flags"] for a, r in self.report["annotators"].items() if r["flags"]}
        self.assertEqual(got, {
            "A02": ["rushing"], "A03": ["rushing"], "A04": ["copying"],
            "A05": ["rushing"], "A08": ["copying"],
        })

    def test_flagged_list(self):
        self.assertEqual(self.summary["flagged"], ["A02", "A03", "A04", "A05", "A08"])

    def test_flags_by_reason(self):
        self.assertEqual(self.summary["flags_by_reason"], {"copying": 2, "rushing": 3})

    def test_3_worst_rusher(self):
        self.assertEqual(self.summary["worst_rusher"], "A03")


if __name__ == "__main__":
    unittest.main()
