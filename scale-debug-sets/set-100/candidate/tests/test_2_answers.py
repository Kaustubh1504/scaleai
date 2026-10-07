import unittest

from tests.helpers import run_against_mock


class TestAnswers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server, cls.report, _ = run_against_mock()

    def test_3_blocked_prompts(self):
        self.assertEqual(self.report["blocked"], ["p09"])

    def test_4_resent_delta(self):
        self.assertEqual(self.report["answers"]["p06"], "Hamlet was written by William Shakespeare.")

    def test_out_of_order_deltas(self):
        self.assertEqual(self.report["answers"]["p02"], "Therefore Socrates is mortal.")

    def test_token_budget(self):
        self.assertEqual(self.report["answers"]["p08"], "The meeting covered hiring")
        self.assertEqual(self.report["finish_reasons"]["p08"], "length")
        self.assertEqual(self.report["finish_reasons"]["p14"], "stop")

    def test_grading(self):
        for prompt_id in ("p01", "p02", "p03", "p14"):
            self.assertIn(prompt_id, self.report["passed"])
        for prompt_id in ("p05", "p08", "p13", "p16"):
            self.assertNotIn(prompt_id, self.report["passed"])

    def test_new_prompts(self):
        self.assertEqual(self.report["new_prompts"], ["p04", "p16"])


if __name__ == "__main__":
    unittest.main()
