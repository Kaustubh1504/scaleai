import unittest

from leasebox.reports import build_report


class TestSummary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.summary = build_report()["summary"]

    def test_completed_and_dead(self):
        self.assertEqual(self.summary["completed_by"], {"W1": 3, "W2": 1, "W3": 3, "W4": 1})
        self.assertEqual(self.summary["dead"], ["T02", "T05"])

    def test_rejections(self):
        self.assertEqual(self.summary["rejected"], {"expired": 4, "not_owner": 2, "invalid": 1})

    def test_wait_stats(self):
        self.assertEqual(self.summary["wait"], {"mean_s": 48.8, "max_s": 230.0})


if __name__ == "__main__":
    unittest.main()
