import unittest

from reviewflow.reports import build_report


class TestPeople(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_reviewer_table(self):
        self.assertEqual(self.report["reviewers"], {
            "rev-01": {"approved": 2, "rejected": 2},
            "rev-02": {"approved": 2, "rejected": 1},
            "lead-01": {"approved": 0, "rejected": 1},
            "lead-02": {"approved": 1, "rejected": 0},
        })

    def test_annotator_submissions(self):
        got = {aid: row["submitted"] for aid, row in self.report["annotators"].items()}
        self.assertEqual(got, {"ann-01": 4, "ann-02": 4, "ann-03": 3, "ann-05": 0})

    def test_annotator_approvals(self):
        got = {aid: row["approved"] for aid, row in self.report["annotators"].items()}
        self.assertEqual(got, {"ann-01": 1, "ann-02": 2, "ann-03": 2, "ann-05": 0})


if __name__ == "__main__":
    unittest.main()
