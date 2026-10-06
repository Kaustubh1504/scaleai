import unittest

from tests.mock_server import API_KEY, MockEmbeddingServer
from vecbatch.reports import build_report


class TestRequests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = MockEmbeddingServer().start()
        cls.report = build_report(cls.server.url, API_KEY)

    @classmethod
    def tearDownClass(cls):
        cls.server.stop()

    def test_request_body(self):
        first = self.server.requests_for("b03")[0]
        self.assertEqual((first["method"], first["path"]), ("POST", "/v1/embeddings"))
        self.assertEqual(first["body"], {
            "model": "embed-small-3",
            "input": [
                "You can reset your password from the account settings page.",
                "Gift cards cannot be exchanged for cash or credit.",
            ],
            "dimensions": 16,
            "metadata": {"batch_id": "b03"},
        })

    def test_every_request_authenticated(self):
        self.assertEqual({r["authorization"] for r in self.server.requests}, {f"Bearer {API_KEY}"})

    def test_1_attempts_per_batch(self):
        attempts = {f"b{n:02d}": len(self.server.requests_for(f"b{n:02d}")) for n in range(1, 9)}
        self.assertEqual(attempts, {"b01": 1, "b02": 2, "b03": 2, "b04": 3,
                                    "b05": 1, "b06": 1, "b07": 1, "b08": 1})

    def test_2_retry_after_honoured(self):
        first, second = (r["t"] for r in self.server.requests_for("b02")[:2])
        self.assertGreaterEqual(round(second - first, 2), 1.0)

    def test_3_concurrency_limit(self):
        self.assertEqual(self.server.peak_in_flight, 2)


if __name__ == "__main__":
    unittest.main()
