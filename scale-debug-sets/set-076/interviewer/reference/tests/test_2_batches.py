import unittest

from tests._harness import run_job


def batch(status, http_status, *docs):
    return {"status": status, "http_status": http_status, "documents": list(docs)}


EXPECTED = {
    "faq-01": batch("ok", 200, "faq-006", "faq-002", "faq-003"),
    "faq-02": batch("ok", 200, "faq-001", "faq-005", "faq-004"),
    "faq-03": batch("ok", 200, "faq-007"),
    "policies-01": batch("failed", 503, "pol-103", "pol-101", "pol-104"),
    "policies-02": batch("ok", 200, "pol-102", "pol-105"),
    "changelog-01": batch("rejected", 200, "chg-201", "chg-203", "chg-202"),
    "changelog-02": batch("ok", 200, "chg-204"),
    "pricing-01": batch("failed", 400, "prc-301", "prc-303", "prc-302"),
}


class TestBatches(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server, cls.sleeps, cls.report = run_job()

    @classmethod
    def tearDownClass(cls):
        cls.server.stop()

    def test_batch_results(self):
        self.maxDiff = None
        self.assertEqual(self.report["batches"], EXPECTED)

    def test_skipped_rows(self):
        self.assertEqual(self.report["skipped"], ["drf-501", "faq-008", "leg-401", "leg-402", "pol-106", "tmp-601"])

    def test_backoff_delays(self):
        self.assertEqual(sorted(self.sleeps.delays), [0.0, 0.0, 0.5, 0.5, 1.0, 2.0])

    def test_job_committed(self):
        self.assertEqual(self.server.commits, [{
            "job_id": "backfill-0412",
            "accepted": ["changelog-02", "faq-01", "faq-02", "faq-03", "policies-02"],
            "documents": 10,
        }])


if __name__ == "__main__":
    unittest.main()
