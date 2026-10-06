import unittest

from tests.helpers import run_against_mock
from tests.mock_server import API_KEY


class TestRequests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server, cls.waits, cls.report = run_against_mock()

    @classmethod
    def tearDownClass(cls):
        cls.server.stop()

    def test_first_batch_body(self):
        body = self.server.embed_requests(batch=0)[0]["body"]
        self.assertEqual(body["model"], "embed-small-3")
        self.assertEqual(body["metadata"], {"batch": 0})
        self.assertEqual(body["input"], [
            "Reset your password from the account settings page and confirm the change by email.",
            "Invoices are generated on the first business day of each month.",
            "To export a project, open the menu and choose Download as CSV.",
            "Annotators should flag images that show faces before submitting a task.",
        ])

    def test_every_request_authenticated(self):
        self.assertEqual({r["auth"] for r in self.server.requests}, {f"Bearer {API_KEY}"})

    def test_concurrency_limit(self):
        self.assertLessEqual(self.server.peak_in_flight, 2)

    def test_attempts_per_batch(self):
        attempts = {b: len(self.server.embed_requests(batch=b)) for b in range(5)}
        self.assertEqual(attempts, {0: 1, 1: 2, 2: 4, 3: 1, 4: 2})

    def test_backoff_waits(self):
        self.assertEqual(sorted(self.waits), [0.5, 0.5, 1.0, 2.0, 2.0])


if __name__ == "__main__":
    unittest.main()
