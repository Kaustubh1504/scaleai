import asyncio
import unittest

from embedindex.reports import build_report
from tests.mock_server import API_KEY, MockEmbeddingServer


async def no_wait(seconds):
    await asyncio.sleep(0)


class TestReport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = MockEmbeddingServer().start()
        cls.summary = build_report(cls.server.url, API_KEY, sleep=no_wait)["summary"]

    @classmethod
    def tearDownClass(cls):
        cls.server.stop()

    def test_document_counts(self):
        self.assertEqual((self.summary["docs"], self.summary["embedded"]), (18, 12))

    def test_by_collection(self):
        self.assertEqual(self.summary["by_collection"], {
            "faq": {"docs": 8, "embedded": 8},
            "kb": {"docs": 6, "embedded": 3},
            "policies": {"docs": 4, "embedded": 1},
        })

    def test_total_tokens(self):
        self.assertEqual(self.summary["total_tokens"], 63)

    def test_usage_fetched_page_by_page(self):
        pages = [r for r in self.server.requests if r["path"] == "/v1/usage"]
        self.assertEqual([p["query"].get("cursor") is None for p in pages], [True, False, False])


if __name__ == "__main__":
    unittest.main()
