import unittest

from tests.harness import SyncRun


class TestSummary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.run_ = SyncRun()
        cls.summary = cls.run_.report()["summary"]

    @classmethod
    def tearDownClass(cls):
        cls.run_.stop()

    def test_status_counts(self):
        self.assertEqual(
            (self.summary["counts"], self.summary["failed_batches"]),
            ({"embedded": 12, "skipped": 4, "failed": 3}, {"products-1": 503}),
        )

    def test_total_tokens(self):
        self.assertEqual(self.summary["total_tokens"], 91)

    def test_cost(self):
        self.assertEqual(self.summary["cost_usd"], 0.0118)


if __name__ == "__main__":
    unittest.main()
