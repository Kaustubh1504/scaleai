import unittest

from revflow.reports import build_report


class TestReviewers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_reviewer_roster(self):
        self.assertEqual(list(self.report["reviewers"]), ["rv-01", "rv-02", "rv-03", "sr-01", "sr-02"])

    def test_reviewer_decisions(self):
        self.assertEqual(self.report["reviewers"], {
            "rv-01": {"claims": 3, "approved": 2, "rejected": 0},
            "rv-02": {"claims": 3, "approved": 0, "rejected": 1},
            "rv-03": {"claims": 3, "approved": 0, "rejected": 2},
            "sr-01": {"claims": 0, "approved": 1, "rejected": 0},
            "sr-02": {"claims": 0, "approved": 0, "rejected": 0},
        })

    def test_review_minutes(self):
        self.assertEqual(self.report["review_minutes"], {"rv-01": 37.5, "rv-02": 30.0, "rv-03": 25.0})


if __name__ == "__main__":
    unittest.main()
