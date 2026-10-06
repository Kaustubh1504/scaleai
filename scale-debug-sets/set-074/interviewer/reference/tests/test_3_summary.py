import unittest

from likert.reports import build_report


class TestSummary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.summary = build_report()["summary"]

    def test_by_rubric(self):
        self.assertEqual(self.summary["by_rubric"], {
            "v1": {"agreed": 3, "contested": 2, "insufficient": 1},
            "v2": {"agreed": 5, "contested": 1, "insufficient": 0},
        })

    def test_contested(self):
        self.assertEqual(self.summary["contested"], ["I04", "I07", "I09"])


if __name__ == "__main__":
    unittest.main()
