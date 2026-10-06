import unittest

from embedq.reports import build_report
from tests.mock_server import API_KEY, MockEmbeddingServer


class TestRequests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.delays = []

        async def record_sleep(seconds):
            cls.delays.append(seconds)

        cls.server = MockEmbeddingServer().start()
        cls.report = build_report(cls.server.url, API_KEY, sleep=record_sleep)

    @classmethod
    def tearDownClass(cls):
        cls.server.stop()

    def test_request_shape(self):
        bodies = [r["body"] for r in self.server.posts()]
        self.assertIn({"model": "embed-s", "input": [
            "How do I reset my password?",
            "Where can I download my invoice?",
            "Is shipping free on orders over fifty dollars?",
        ]}, bodies)
        self.assertTrue(all(1 <= len(b["input"]) <= 3 for b in bodies))
        self.assertEqual({r["authorization"] for r in self.server.requests}, {f"Bearer {API_KEY}"})

    def test_concurrency_limit(self):
        self.assertLessEqual(self.server.max_in_flight, 2)

    def test_requests_per_model(self):
        counts = {m: len(self.server.posts(m)) for m in ("embed-s", "embed-l")}
        self.assertEqual(counts, {"embed-s": 6, "embed-l": 7})

    def test_backoff_delays(self):
        self.assertEqual(sorted(self.delays), [0.1, 0.2, 1.0])


if __name__ == "__main__":
    unittest.main()
