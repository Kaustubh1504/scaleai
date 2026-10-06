import unittest

from evalclient.reports import build_report
from tests.mock_server import API_KEY, MockModelServer


class TestReport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = MockModelServer().start()
        cls.summary = build_report(cls.server.url, API_KEY)["summary"]

    @classmethod
    def tearDownClass(cls):
        cls.server.stop()

    def test_counts(self):
        self.assertEqual(self.summary["counts"], {"ok": 7, "parse_error": 1, "http_error": 2})

    def test_scores(self):
        self.assertEqual((self.summary["mean_score"], self.summary["pass_rate"]), (6.5, 0.714))

    def test_usage_totals(self):
        self.assertEqual(self.summary["total_tokens"], 3039)

    def test_latency(self):
        self.assertEqual(self.summary["p50_latency_s"], 0.9)

    def test_usage_fetched_page_by_page(self):
        pages = [r for r in self.server.requests if r["path"] == "/v1/usage"]
        self.assertEqual([p["query"].get("cursor") is None for p in pages], [True, False, False])


if __name__ == "__main__":
    unittest.main()
