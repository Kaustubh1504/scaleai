import unittest

from tests.mock_server import API_KEY, MockEmbeddingServer
from vecbatch.reports import build_report


class TestReport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = MockEmbeddingServer().start()
        cls.report = build_report(cls.server.url, API_KEY)

    @classmethod
    def tearDownClass(cls):
        cls.server.stop()

    def test_counts(self):
        self.assertEqual(self.report["counts"], {"embedded": 9, "failed": 6})

    def test_usage_starts_from_the_beginning(self):
        first = next(r for r in self.server.requests if r["path"] == "/v1/usage")
        self.assertEqual(first["query"], {"limit": "3"})

    def test_5_total_tokens(self):
        self.assertEqual(self.report["total_tokens"], 121)

    def test_6_near_duplicates(self):
        self.assertEqual(self.report["near_duplicates"], [
            ["d03", "d12", 1.0],
            ["d01", "d05", 0.956],
            ["d02", "d11", 0.945],
        ])


if __name__ == "__main__":
    unittest.main()
