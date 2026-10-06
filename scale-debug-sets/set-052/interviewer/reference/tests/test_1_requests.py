import asyncio
import unittest

from embedindex.reports import build_report
from tests.mock_server import API_KEY, MockEmbeddingServer


class TestRequests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = MockEmbeddingServer().start()
        cls.sleeps = []

        async def record_sleep(seconds):
            cls.sleeps.append(seconds)
            await asyncio.sleep(0)

        cls.report = build_report(cls.server.url, API_KEY, sleep=record_sleep)

    @classmethod
    def tearDownClass(cls):
        cls.server.stop()

    def test_request_body(self):
        first = self.server.posts_for("faq-01")[0]
        self.assertEqual(first["path"], "/v1/embeddings")
        self.assertEqual(first["body"], {
            "model": "embed-small-3",
            "input": [
                "How do I reset my password?",
                "Where can I download my invoices?",
                "Can I change the billing email on my account?",
            ],
            "dimensions": 4,
            "user": "faq-01",
        })

    def test_every_request_authenticated(self):
        self.assertEqual({r["authorization"] for r in self.server.requests}, {f"Bearer {API_KEY}"})

    def test_attempts_seen_by_server(self):
        attempts = {b: len(self.server.posts_for(b)) for b in self.report["batches"]}
        self.assertEqual(attempts, {"faq-01": 1, "faq-02": 2, "faq-03": 1, "kb-01": 3,
                                    "kb-02": 1, "policies-01": 3, "policies-02": 1})

    def test_concurrency_limit(self):
        self.assertLessEqual(self.server.max_in_flight, 2)

    def test_backoff_waits(self):
        self.assertEqual(sorted(self.sleeps), [0.01, 0.05, 0.05, 0.1, 0.1])


if __name__ == "__main__":
    unittest.main()
