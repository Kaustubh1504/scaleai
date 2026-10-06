import unittest

from tests.mock_server import API_KEY, MockApiServer
from vecsync.runner import build_report


class TestReport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = MockApiServer().start()
        cls.report = build_report(cls.server.url, API_KEY)

    @classmethod
    def tearDownClass(cls):
        cls.server.stop()

    def test_commit_outcomes(self):
        self.assertEqual(self.report["commit"], {"committed": ["b1", "b2", "b3"], "failed": ["b6"]})

    def test_total_tokens(self):
        self.assertEqual(self.report["total_tokens"], 78)


if __name__ == "__main__":
    unittest.main()
