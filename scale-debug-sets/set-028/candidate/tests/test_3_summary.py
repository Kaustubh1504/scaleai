import unittest

from embedq.reports import build_report
from tests.mock_server import API_KEY, MockEmbeddingServer


class TestSummary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        async def no_sleep(seconds):
            return None

        cls.server = MockEmbeddingServer().start()
        cls.summary = build_report(cls.server.url, API_KEY, sleep=no_sleep)["summary"]

    @classmethod
    def tearDownClass(cls):
        cls.server.stop()

    def test_document_counts(self):
        counts = {m: (s["ok"], s["failed"]) for m, s in self.summary.items()}
        self.assertEqual(counts, {"embed-s": (12, 3), "embed-l": (10, 5)})

    def test_billed_tokens(self):
        tokens = {m: s["billed_tokens"] for m, s in self.summary.items()}
        self.assertEqual(tokens, {"embed-s": 63, "embed-l": 90})

    def test_usage_read_page_by_page(self):
        pages = [r for r in self.server.requests if r["path"] == "/v1/usage"]
        self.assertEqual([p["query"].get("cursor") is None for p in pages], [True, False, False])


if __name__ == "__main__":
    unittest.main()
