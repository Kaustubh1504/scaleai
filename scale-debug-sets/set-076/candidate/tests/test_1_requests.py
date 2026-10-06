import unittest

from tests._harness import run_job
from tests.mock_server import API_KEY


class TestRequests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server, cls.sleeps, cls.report = run_job()

    @classmethod
    def tearDownClass(cls):
        cls.server.stop()

    def test_request_body(self):
        first = self.server.embedding_requests("faq-01")[0]
        self.assertEqual(first["body"], {
            "model": "embed-small-3",
            "collection": "faq",
            "batch_id": "faq-01",
            "dimensions": 4,
            "input": [
                {"id": "faq-006", "text": "How do I contact support?"},
                {"id": "faq-002", "text": "Where can I download invoices?"},
                {"id": "faq-003", "text": "Can I change my username?"},
            ],
        })

    def test_every_request_authenticated(self):
        self.assertEqual({r["authorization"] for r in self.server.requests}, {f"Bearer {API_KEY}"})

    def test_batches_sent(self):
        sizes = {}
        for r in self.server.embedding_requests():
            sizes[r["body"]["batch_id"]] = len(r["body"]["input"])
        self.assertEqual(sizes, {
            "faq-01": 3, "faq-02": 3, "faq-03": 1, "policies-01": 3, "policies-02": 2,
            "changelog-01": 3, "changelog-02": 1, "pricing-01": 3,
        })

    def test_concurrency_limit(self):
        self.assertEqual(self.server.max_in_flight, 2)

    def test_attempts_per_batch(self):
        attempts = {bid: len(self.server.embedding_requests(bid)) for bid in self.report["batches"]}
        self.assertEqual(attempts, {
            "faq-01": 1, "faq-02": 3, "faq-03": 1, "policies-01": 4, "policies-02": 2,
            "changelog-01": 1, "changelog-02": 1, "pricing-01": 1,
        })


if __name__ == "__main__":
    unittest.main()
