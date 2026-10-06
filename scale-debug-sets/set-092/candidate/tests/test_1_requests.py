import unittest

from tests.harness import SyncRun
from tests.mock_server import API_KEY


class TestRequests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.run_ = SyncRun()
        cls.report = cls.run_.report()
        cls.server = cls.run_.server

    @classmethod
    def tearDownClass(cls):
        cls.run_.stop()

    def test_embedding_request_body(self):
        body = self.server.embedding_requests("faq-0")[0]["body"]
        self.assertEqual(body, {
            "model": "embed-large-3",
            "dimensions": 2,
            "input": [
                "How do I reset my password?",
                "Where can I see my payout history?",
                "How long does a task review usually take?",
            ],
            "documents": [
                {"id": "f01", "updated_at": "2026-09-01T10:00:00"},
                {"id": "f02", "updated_at": "2026-09-02T08:30:00"},
                {"id": "f03", "updated_at": "2026-09-03T09:15:00"},
            ],
            "metadata": {"batch_id": "faq-0"},
        })

    def test_concurrency_limit(self):
        self.assertLessEqual(self.server.max_in_flight, 2)

    def test_backoff_delays(self):
        self.assertEqual(sorted(self.run_.delays), [0.25, 0.5, 0.5, 1.0])

    def test_attempts_per_batch(self):
        batches = ["faq-0", "faq-1", "faq-2", "policies-0", "products-0", "products-1"]
        attempts = {b: len(self.server.embedding_requests(b)) for b in batches}
        self.assertEqual(attempts, {"faq-0": 1, "faq-1": 2, "faq-2": 1,
                                    "policies-0": 2, "products-0": 1, "products-1": 3})
        self.assertEqual(len(self.server.embedding_requests()), 10)

    def test_every_request_authenticated(self):
        self.assertEqual({r["authorization"] for r in self.server.requests}, {f"Bearer {API_KEY}"})

    def test_index_listing_pages(self):
        pages = [r["query"] for r in self.server.requests if r["path"] == "/v1/index/policies"]
        self.assertEqual([("page_token" in q, q["limit"]) for q in pages],
                         [(False, "4"), (True, "4"), (True, "4")])


if __name__ == "__main__":
    unittest.main()
