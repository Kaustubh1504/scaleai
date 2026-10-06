import unittest

from embedclient.report import build_report
from tests.mock_server import API_KEY, MockEmbeddingServer


class TestSummary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = MockEmbeddingServer().start()
        cls.summary = build_report(cls.server.url, API_KEY)["summary"]

    @classmethod
    def tearDownClass(cls):
        cls.server.stop()

    def test_embedded_count(self):
        self.assertEqual(self.summary["embedded"], 13)

    def test_missing_docs(self):
        self.assertEqual(self.summary["missing_docs"], ["d11", "d12", "d13", "d17", "d18", "d19"])

    def test_total_tokens(self):
        self.assertEqual(self.summary["total_tokens"], 91)

    def test_stale_ids(self):
        self.assertEqual(self.summary["stale_ids"], ["d27", "d31", "d40"])


if __name__ == "__main__":
    unittest.main()
