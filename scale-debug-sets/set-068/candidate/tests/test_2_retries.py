import unittest

from embedclient.reports import build_report
from tests.mock_server import API_KEY, MockEmbeddingServer


class TestRetries(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = MockEmbeddingServer().start()
        cls.batches = build_report(cls.server.url, API_KEY)["batches"]

    @classmethod
    def tearDownClass(cls):
        cls.server.stop()

    def test_final_statuses(self):
        self.assertEqual({b: (row["status"], row["http_status"]) for b, row in self.batches.items()}, {
            "b01": ("ok", 200), "b02": ("ok", 200), "b03": ("ok", 200), "b04": ("failed", 503),
            "b05": ("failed", 400), "b06": ("ok", 200), "b07": ("ok", 200),
        })

    def test_attempts_per_batch(self):
        seen = {b: len(self.server.requests_for(b)) for b in self.batches}
        reported = {b: row["attempts"] for b, row in self.batches.items()}
        expected = {"b01": 1, "b02": 2, "b03": 1, "b04": 3, "b05": 1, "b06": 2, "b07": 1}
        self.assertEqual((seen, reported), (expected, expected))

    def test_retry_after_respected(self):
        first, second = self.server.requests_for("b02")
        self.assertGreaterEqual(round(second["at"] - first["at"], 2), 0.3)


if __name__ == "__main__":
    unittest.main()
