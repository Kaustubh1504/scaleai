import unittest

from embedclient.report import build_report
from tests.mock_server import API_KEY, MockEmbeddingServer


class TestRequests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = MockEmbeddingServer().start()
        cls.report = build_report(cls.server.url, API_KEY)

    @classmethod
    def tearDownClass(cls):
        cls.server.stop()

    def test_payload_shape(self):
        first = self.server.embed_calls("b1")[0]
        self.assertEqual(first["method"], "POST")
        self.assertEqual(first["auth"], f"Bearer {API_KEY}")
        self.assertEqual(first["body"], {
            "model": "embed-small-3",
            "input": [
                "Label every visible object in the frame",
                "Partially hidden objects still get a box",
                "Objects cut off by the image edge are truncated",
            ],
            "metadata": {"batch": "b1"},
        })

    def test_concurrency_limit(self):
        self.assertLessEqual(self.server.max_in_flight, 2)

    def test_retry_after_honoured(self):
        calls = self.server.embed_calls("b2")
        self.assertEqual(len(calls), 2)
        self.assertGreaterEqual(calls[1]["at"] - calls[0]["at"], 0.2)

    def test_attempts_per_batch(self):
        attempts = {b: len(self.server.embed_calls(b)) for b in self.report["batches"]}
        self.assertEqual(attempts, {"b1": 1, "b2": 2, "b3": 1, "b4": 3, "b5": 1, "b6": 1, "b7": 1})

    def test_index_listed_page_by_page(self):
        pages = [r for r in self.server.requests if r["path"] == "/v1/index"]
        self.assertEqual([(p["query"]["limit"], "cursor" in p["query"]) for p in pages],
                         [("4", False), ("4", True), ("4", True)])


if __name__ == "__main__":
    unittest.main()
