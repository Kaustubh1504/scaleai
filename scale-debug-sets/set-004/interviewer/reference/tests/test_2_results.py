import unittest

from evalclient.reports import build_report
from tests.mock_server import API_KEY, MockModelServer


def ok(score, passed):
    return {"status": "ok", "http_status": 200, "score": score, "passed": passed}


def failed(status, http_status):
    return {"status": status, "http_status": http_status, "score": None, "passed": None}


EXPECTED = {
    "r01": ok(8.0, True),
    "r02": ok(3.0, False),
    "r03": ok(6.0, True),
    "r04": ok(9.0, True),
    "r05": failed("http_error", 400),
    "r06": failed("parse_error", 200),
    "r07": failed("http_error", 503),
    "r08": ok(7.5, True),
    "r09": ok(2.0, False),
    "r10": ok(10.0, True),
}


class TestResults(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = MockModelServer().start()
        cls.results = build_report(cls.server.url, API_KEY)["results"]

    @classmethod
    def tearDownClass(cls):
        cls.server.stop()

    def test_statuses(self):
        self.assertEqual({k: v["status"] for k, v in self.results.items()},
                         {k: v["status"] for k, v in EXPECTED.items()})

    def test_results(self):
        self.maxDiff = None
        self.assertEqual(self.results, EXPECTED)


if __name__ == "__main__":
    unittest.main()
