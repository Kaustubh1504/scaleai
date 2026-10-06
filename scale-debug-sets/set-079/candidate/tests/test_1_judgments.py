import unittest

from judgescore.reports import build_report


class TestJudgments(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_sample_scores(self):
        self.maxDiff = None
        self.assertEqual(self.report["samples"], {
            "s01": 0.82, "s02": 0.73, "s03": 1.0, "s04": 0.55, "s05": 0.33, "s06": 0.8,
            "s07": 0.63, "s08": 0.83, "s09": 0.17, "s10": 0.9, "s11": 0.67, "s12": 0.83,
            "s13": 0.83, "s14": 0.78, "s15": 1.0, "s16": 0.52, "s17": 0.67, "s18": 0.83,
        })

    def test_unscored(self):
        self.assertEqual(self.report["unscored"], ["s19", "s20"])

    def test_judge_counts(self):
        self.assertEqual(self.report["judges"], {"judge-a": 17, "judge-b": 13})

    def test_parse_failures(self):
        self.assertEqual(self.report["parse_failures"], ["j10", "j15", "j32", "j34", "line-21"])


if __name__ == "__main__":
    unittest.main()
