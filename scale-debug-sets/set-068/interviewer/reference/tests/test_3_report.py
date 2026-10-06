import unittest

from embedclient.reports import build_report
from tests.mock_server import API_KEY, MockEmbeddingServer


class TestReport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = MockEmbeddingServer().start()
        cls.report = build_report(cls.server.url, API_KEY)

    @classmethod
    def tearDownClass(cls):
        cls.server.stop()

    def test_doc_norms(self):
        norms = {d: row["norm"] for d, row in self.report["docs"].items() if row["status"] == "ok"}
        self.assertEqual(norms, {
            "faq-01": 7.28, "faq-02": 10.05, "faq-03": 8.367,
            "leg-01": 8.775, "leg-02": 7.483, "leg-03": 8.367,
            "sup-01": 6.403, "sup-03": 7.81, "sup-04": 10.77,
            "sup-05": 10.247, "sup-06": 8.124, "sup-08": 6.164,
            "faq-07": 8.124, "faq-08": 9.95, "faq-09": 6.708,
        })

    def test_failed_docs(self):
        failed = {d: row["http_status"] for d, row in self.report["docs"].items() if row["status"] == "failed"}
        self.assertEqual(failed, {"faq-04": 503, "faq-05": 503, "faq-06": 503,
                                  "leg-04": 400, "leg-05": 400, "leg-06": 400})

    def test_summary(self):
        self.assertEqual(self.report["summary"], {
            "embedded": 15, "failed": 6, "total_tokens": 104, "tokens_per_doc": 6.93,
            "by_collection": {"faq": 6, "legal": 3, "support": 6},
        })


if __name__ == "__main__":
    unittest.main()
