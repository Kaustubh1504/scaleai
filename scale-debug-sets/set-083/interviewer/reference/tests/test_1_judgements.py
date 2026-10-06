import unittest

from prefpairs.reports import build_report


class TestJudgements(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_labeler_quality(self):
        self.maxDiff = None
        self.assertEqual(self.report["labelers"], {
            "lab-01": {"checks": 2, "accuracy": 1.0, "excluded": False},
            "lab-02": {"checks": 2, "accuracy": 1.0, "excluded": False},
            "lab-03": {"checks": 2, "accuracy": 1.0, "excluded": False},
            "lab-04": {"checks": 2, "accuracy": 1.0, "excluded": False},
            "lab-05": {"checks": 3, "accuracy": 0.333, "excluded": True},
            "lab-06": {"checks": 0, "accuracy": None, "excluded": False},
            "lab-07": {"checks": 0, "accuracy": None, "excluded": False},
            "lab-08": {"checks": 0, "accuracy": None, "excluded": False},
            "lab-09": {"checks": 4, "accuracy": 0.75, "excluded": False},
        })

    def test_pair_margins(self):
        margins = {pid: r["margin"] for pid, r in self.report["pairs"].items()}
        self.assertEqual(margins, {
            "P01": 1.67, "P02": -2.0, "P03": 0.0, "P04": -1.5, "P05": 2.5, "P06": 0.5, "P07": 0.33,
            "P08": 1.33, "P09": None, "P10": 1.5, "P11": 2.5, "P12": -0.67, "P13": None, "P14": -1.0,
        })

    def test_verdicts_and_votes(self):
        got = {pid: (r["verdict"], r["votes"]) for pid, r in self.report["pairs"].items()}
        self.assertEqual(got, {
            "P01": ("A", 3), "P02": ("B", 3), "P03": ("tie", 3), "P04": ("B", 2), "P05": ("A", 2),
            "P06": ("A", 2), "P07": ("tie", 3), "P08": ("A", 3), "P09": ("insufficient", 1),
            "P10": ("A", 2), "P11": ("A", 2), "P12": ("B", 3), "P13": ("insufficient", 1),
            "P14": ("B", 2),
        })


if __name__ == "__main__":
    unittest.main()
