import unittest

from tests.helpers import run_against_mock
from tests.mock_server import API_KEY


class TestRequests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server, cls.report = run_against_mock()

    def test_create_payload(self):
        first = self.server.creates_for("legal")[0]
        self.assertEqual(first["path"], "/v1/batches")
        self.assertEqual(first["body"], {
            "model": "embed-legal-v1",
            "collection": "legal",
            "inputs": [
                {"id": "lg-01", "text": "This agreement is governed by the laws of Ontario."},
                {"id": "lg-02", "text": "Termination requires thirty days written notice."},
                {"id": "lg-03", "text": "Liability is capped at fees paid in the prior year."},
            ],
        })
        self.assertEqual(self.server.creates_for("faq")[0]["body"]["model"], "embed-small-v2")

    def test_every_request_authenticated(self):
        self.assertEqual({r["authorization"] for r in self.server.requests}, {f"Bearer {API_KEY}"})

    def test_concurrency_cap(self):
        self.assertLessEqual(self.server.max_inflight, 2)


if __name__ == "__main__":
    unittest.main()
