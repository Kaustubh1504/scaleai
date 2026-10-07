import unittest

from tests.helpers import run_against_mock


class TestReport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server, cls.report, _ = run_against_mock()

    def test_5_failed_prompts(self):
        self.assertEqual(self.report["failed"], {
            "p07": "HTTP 400",
            "p10": "stream ended before done",
            "p11": "HTTP 503",
        })

    def test_6_regressions(self):
        self.assertEqual(self.report["regressions"], ["p05", "p08", "p13"])

    def test_suite_scores(self):
        suites = self.report["suites"]
        self.assertEqual(suites["math"], {"graded": 3, "passed": 1})
        self.assertEqual(suites["reasoning"], {"graded": 2, "passed": 1})
        self.assertEqual(suites["summaries"], {"graded": 1, "passed": 0})
        self.assertEqual(suites["trivia"], {"graded": 3, "passed": 3})

    def test_model(self):
        self.assertEqual(self.report["model"], "relay-small")


if __name__ == "__main__":
    unittest.main()
