import unittest

from tests.helpers import run_against_mock
from tests.mock_server import API_KEY


class TestRequests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server, cls.report, cls.sleep = run_against_mock()

    def test_1_request_ids_match_prompts(self):
        streams = [r for r in self.server.requests if r["path"] == "/v1/complete"]
        self.assertTrue(streams)
        sent, expected = {}, {}
        for prompt_id in sorted({r["prompt_id"] for r in streams}):
            sent[prompt_id] = sorted(r["request_id"] for r in self.server.completions_for(prompt_id))
            expected[prompt_id] = [f"{prompt_id}-{n}" for n in range(1, len(sent[prompt_id]) + 1)]
        self.assertEqual(sent, expected)

    def test_2_attempts_for_unavailable_prompt(self):
        self.assertEqual(len(self.server.completions_for("p11")), 4)

    def test_every_request_authenticated(self):
        self.assertEqual({r["authorization"] for r in self.server.requests}, {f"Bearer {API_KEY}"})

    def test_rate_limited_prompt_recovers(self):
        self.assertEqual(len(self.server.completions_for("p03")), 3)
        self.assertEqual(self.sleep.delays.count(1.5), 1)
        self.assertEqual(self.report["answers"]["p03"], "The capital is Canberra.")


if __name__ == "__main__":
    unittest.main()
