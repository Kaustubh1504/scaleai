import unittest

from evalclient.reports import build_report
from tests.mock_server import API_KEY, MockModelServer

SYSTEM_PROMPT = "You are a strict grader. Reply with a JSON object containing score (0-10) and passed."


class TestRequests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = MockModelServer().start()
        cls.report = build_report(cls.server.url, API_KEY)

    @classmethod
    def tearDownClass(cls):
        cls.server.stop()

    def test_request_body(self):
        first = self.server.requests_for("r02")[0]
        self.assertEqual(first["method"], "POST")
        self.assertEqual(first["path"], "/v1/chat/completions")
        self.assertEqual(first["body"], {
            "model": "judge-large-2",
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": "Question: What is 17 * 3?\nAnswer: 41"},
            ],
            "max_tokens": 200,
            "temperature": 0,
            "metadata": {"request_id": "r02"},
        })

    def test_every_request_authenticated(self):
        auth = {r["headers"]["authorization"] for r in self.server.requests}
        self.assertEqual(auth, {f"Bearer {API_KEY}"})

    def test_send_order(self):
        self.assertEqual(self.report["order"],
                         ["r02", "r03", "r07", "r01", "r05", "r09", "r04", "r06", "r08", "r10"])

    def test_attempts_per_request(self):
        attempts = {rid: len(self.server.requests_for(rid)) for rid in self.report["order"]}
        self.assertEqual(attempts, {
            "r02": 1, "r03": 4, "r07": 4, "r01": 1, "r05": 1,
            "r09": 1, "r04": 2, "r06": 1, "r08": 1, "r10": 2,
        })

    def test_blank_answers_not_sent(self):
        self.assertEqual(self.server.requests_for("r11") + self.server.requests_for("r12"), [])


if __name__ == "__main__":
    unittest.main()
