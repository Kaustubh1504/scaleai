import unittest

from tests.mock_server import API_KEY, MockApiServer
from vecsync.runner import build_report


class TestRequests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = MockApiServer().start()
        cls.report = build_report(cls.server.url, API_KEY)

    @classmethod
    def tearDownClass(cls):
        cls.server.stop()

    def test_dataset_fully_read(self):
        self.assertEqual((self.report["fetched"], self.report["pages"]), (27, 6))

    def test_concurrency_limit(self):
        self.assertEqual(self.server.max_in_flight, 2)

    def test_backoff_between_attempts(self):
        times = [r["at"] for r in self.server.embedding_requests("b2")]
        gaps = [round(b - a, 3) for a, b in zip(times, times[1:])]
        self.assertEqual(len(gaps), 2)
        self.assertTrue(gaps[0] >= 0.09 and gaps[1] >= 0.19, f"gaps between b2 attempts: {gaps}")

    def test_attempts_per_batch(self):
        attempts = {f"b{n}": len(self.server.embedding_requests(f"b{n}")) for n in range(1, 7)}
        self.assertEqual(attempts, {"b1": 1, "b2": 3, "b3": 2, "b4": 1, "b5": 1, "b6": 1})

    def test_request_body(self):
        first = self.server.embedding_requests("b1")[0]
        self.assertEqual(first["authorization"], f"Bearer {API_KEY}")
        self.assertEqual(first["body"], {
            "model": "embed-small-3",
            "input": ["How do I reset my password?", "Where can I download invoices?",
                      "Can I change the billing email?", "How do I add a teammate?"],
            "dimensions": 4,
            "metadata": {"batch_id": "b1"},
        })


if __name__ == "__main__":
    unittest.main()
