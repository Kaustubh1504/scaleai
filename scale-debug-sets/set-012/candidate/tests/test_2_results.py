import unittest

from tests.mock_server import API_KEY, MockEmbeddingServer
from vecbatch.reports import build_report


class TestResults(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = MockEmbeddingServer().start()
        cls.documents = build_report(cls.server.url, API_KEY)["documents"]

    @classmethod
    def tearDownClass(cls):
        cls.server.stop()

    def test_skipped_documents_not_sent(self):
        self.assertEqual([d for d in ("d16", "d17", "d18") if d in self.documents], [])

    def test_embedded_documents(self):
        embedded = sorted(d for d, status in self.documents.items() if status == "embedded")
        self.assertEqual(embedded, ["d01", "d02", "d03", "d04", "d05", "d06", "d11", "d12", "d15"])

    def test_4_failed_documents(self):
        failed = {d: status for d, status in self.documents.items() if status != "embedded"}
        self.assertEqual(failed, {
            "d07": "http_error", "d08": "http_error",
            "d09": "bad_json", "d10": "bad_json",
            "d13": "invalid", "d14": "invalid",
        })


if __name__ == "__main__":
    unittest.main()
