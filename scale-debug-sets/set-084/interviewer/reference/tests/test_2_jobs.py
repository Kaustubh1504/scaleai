import unittest

from tests.helpers import run_against_mock, waits_for


class TestJobLifecycle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server, cls.report = run_against_mock()

    def test_rate_limit_honours_retry_after(self):
        self.assertEqual(len(self.server.creates_for("legal")), 2)
        self.assertEqual(waits_for(self.report, "legal/1", "retry"), [["legal/1", "retry", 0.12]])

    def test_transient_errors_retried(self):
        self.assertEqual(len(self.server.creates_for("product")), 3)
        self.assertEqual(sorted(d for d in self.report["embedded"] if d.startswith("pr-")), ["pr-01", "pr-02"])

    def test_polls_wait_between_checks(self):
        job_id = self.server.job_id_for("news", "nw-01")
        self.assertEqual(len(self.server.polls_for(job_id)), 4)
        self.assertEqual(waits_for(self.report, "news/1", "poll"), [["news/1", "poll", 0.01]] * 3)


if __name__ == "__main__":
    unittest.main()
