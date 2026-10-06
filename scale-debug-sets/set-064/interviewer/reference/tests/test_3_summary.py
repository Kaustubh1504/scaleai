import unittest

from nightshift.report import build_report


class TestSummary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.summary = build_report()["summary"]

    def test_queues_in_summary(self):
        self.assertEqual(sorted(self.summary["attempts_by_queue"]), ["etl", "ops", "reports", "training"])

    def test_5_attempts_for_etl_and_ops(self):
        attempts = self.summary["attempts_by_queue"]
        self.assertEqual({q: attempts[q] for q in ("etl", "ops")}, {"etl": 5, "ops": 5})

    def test_6_late_jobs(self):
        self.assertEqual(self.summary["late_jobs"], ["ops-2", "ops-3"])


if __name__ == "__main__":
    unittest.main()
