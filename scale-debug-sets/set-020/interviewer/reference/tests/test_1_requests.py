import unittest

from labelbatch.reports import build_report
from tests.mock_server import API_KEY, MockBatchServer


class TestRequests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = MockBatchServer().start()
        cls.report = build_report(cls.server.url, API_KEY)

    @classmethod
    def tearDownClass(cls):
        cls.server.stop()

    def test_submit_body(self):
        first = self.server.submits_for("S1")[0]
        self.assertEqual(first["path"], "/v1/batches")
        self.assertEqual(first["auth"], f"Bearer {API_KEY}")
        self.assertEqual(first["body"], {
            "model": "vision-tagger-3",
            "shard": "S1",
            "inputs": [
                {"id": "R01", "text": "tabby cat on a windowsill"},
                {"id": "R02", "text": "golden retriever puppy"},
                {"id": "R03", "text": "blurry photo of a cat toy"},
            ],
        })

    def test_rate_limited_submit_retried(self):
        self.assertEqual(len(self.server.submits_for("S3")), 2)

    def test_1_concurrency_limit(self):
        self.assertLessEqual(self.server.peak_inflight, 2)

    def test_2_every_batch_archived(self):
        self.assertEqual(sorted(self.server.archived),
                         ["batch_s1", "batch_s2", "batch_s3", "batch_s4", "batch_s5"])


if __name__ == "__main__":
    unittest.main()
