import unittest

from embedclient.reports import build_report
from tests.mock_server import API_KEY, MockEmbeddingServer


class TestRequests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = MockEmbeddingServer().start()
        cls.report = build_report(cls.server.url, API_KEY)

    @classmethod
    def tearDownClass(cls):
        cls.server.stop()

    def test_request_body(self):
        first = self.server.requests_for("b01")[0]
        self.assertEqual(first["body"], {
            "model": "embed-small-3",
            "input": ["How do I reset my password", "Where can I download my invoices",
                      "Can I change the billing email"],
            "metadata": {"batch_id": "b01", "doc_ids": ["faq-01", "faq-02", "faq-03"],
                         "newest_update": "2026-04-03T08:15:00"},
        })

    def test_batches_sent(self):
        sent = {r["body"]["metadata"]["batch_id"]: r["body"]["metadata"]["doc_ids"] for r in self.server.requests}
        self.assertEqual(sent, {
            "b01": ["faq-01", "faq-02", "faq-03"], "b02": ["leg-01", "leg-02", "leg-03"],
            "b03": ["sup-01", "sup-03", "sup-04"], "b04": ["faq-04", "faq-05", "faq-06"],
            "b05": ["leg-04", "leg-05", "leg-06"], "b06": ["sup-05", "sup-06", "sup-08"],
            "b07": ["faq-07", "faq-08", "faq-09"],
        })
        self.assertEqual({r["authorization"] for r in self.server.requests}, {f"Bearer {API_KEY}"})

    def test_concurrency_limit(self):
        self.assertLessEqual(self.server.max_in_flight, 2)


if __name__ == "__main__":
    unittest.main()
