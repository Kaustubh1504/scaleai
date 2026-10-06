import unittest

from labelbatch.reports import build_report
from tests.mock_server import API_KEY, MockBatchServer


class TestSummary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = MockBatchServer().start()
        cls.summary = build_report(cls.server.url, API_KEY)["summary"]

    @classmethod
    def tearDownClass(cls):
        cls.server.stop()

    def test_shard_statuses(self):
        self.assertEqual(self.summary["shards"],
                         {"S1": "completed", "S2": "completed", "S3": "completed", "S4": "failed", "S5": "completed"})

    def test_total_tokens(self):
        self.assertEqual(self.summary["total_tokens"], 8815)

    def test_6_cost(self):
        self.assertEqual(self.summary["cost_usd"], 0.1763)


if __name__ == "__main__":
    unittest.main()
