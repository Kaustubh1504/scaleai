import unittest

from triage.reports import build_report


class TestReviewQueue(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_queue_order(self):
        self.assertEqual(self.report["queue"], [
            "P005", "P012", "P018", "P013", "P024", "P010", "P019",
            "P006", "P016", "P015", "P021", "P014", "P020",
        ])

    def test_assignments(self):
        self.assertEqual(self.report["assignments"], {
            "R01": ["P012", "P010"],
            "R02": ["P005", "P013", "P024"],
            "R03": ["P015"],
            "R04": [],
            "R06": ["P019"],
            "R08": ["P006"],
            "R09": [],
            "R10": ["P016"],
        })

    def test_backlog(self):
        self.assertEqual(self.report["backlog"], ["P018", "P021", "P014", "P020"])


if __name__ == "__main__":
    unittest.main()
