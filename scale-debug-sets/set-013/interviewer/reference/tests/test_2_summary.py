import unittest

from fraudscan.reports import build_report


class TestSummary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.summary = build_report()["summary"]

    def test_flagged_annotators(self):
        self.assertEqual(self.summary["flagged"], ["ann-02", "ann-03", "ann-04", "ann-05", "ann-08", "ann-09"])

    def test_copy_tasks(self):
        self.assertEqual(self.summary["copy_tasks"], {
            "T3": ["ann-03", "ann-05"],
            "T5": ["ann-03", "ann-08"],
            "T6": ["ann-05", "ann-08"],
        })

    def test_rejected_submissions(self):
        self.assertEqual(self.summary["rejected"], ["s13"])


if __name__ == "__main__":
    unittest.main()
