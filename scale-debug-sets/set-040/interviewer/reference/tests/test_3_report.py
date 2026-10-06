import unittest

from jobsim.reports import build_report


class TestReport(unittest.TestCase):
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        cls.summary = build_report()["summary"]

    def test_teams(self):
        self.assertEqual(self.summary["teams"], {
            "bi": {"jobs": 5, "succeeded": 4, "busy_min": 105},
            "etl": {"jobs": 6, "succeeded": 4, "busy_min": 205},
            "ml": {"jobs": 4, "succeeded": 3, "busy_min": 90},
            "ops": {"jobs": 3, "succeeded": 0, "busy_min": 10},
        })

    def test_late(self):
        self.assertEqual(self.summary["late"], ["a6"])

    def test_utilization(self):
        self.assertEqual(self.summary["utilization"], 0.394)


if __name__ == "__main__":
    unittest.main()
