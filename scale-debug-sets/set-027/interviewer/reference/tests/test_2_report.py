import unittest

from leasebeat.reports import build_report


class TestReport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_status(self):
        done = sorted(t for t, s in self.report["status"].items() if s == "done")
        self.assertEqual(done, ["T01", "T02", "T03", "T04", "T05", "T08", "T09", "T10"])

    def test_completed_by(self):
        self.assertEqual(self.report["completed_by"], {
            "w1": ["T08", "T05", "T02"],
            "w2": ["T01"],
            "w3": ["T04", "T10"],
            "w4": ["T03"],
            "w5": ["T09"],
        })

    def test_mean_wait(self):
        self.assertEqual(self.report["mean_wait_s"], 821.5)


if __name__ == "__main__":
    unittest.main()
