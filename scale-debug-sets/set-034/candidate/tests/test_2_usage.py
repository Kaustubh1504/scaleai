import unittest

from meterbill.reports import build_report


class TestUsage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.usage = build_report()["usage"]

    def test_allowed_and_throttled_counts(self):
        got = {t: (u["allowed"], u["throttled"]) for t, u in self.usage.items()}
        self.assertEqual(got, {
            "t-acme": (5, 1), "t-bolt": (7, 0), "t-cove": (3, 1), "t-dune": (4, 0), "t-echo": (0, 2),
            "t-fern": (4, 2), "t-gale": (5, 1), "t-hive": (2, 0), "t-iris": (1, 0), "t-jade": (1, 0),
        })

    def test_billable_tokens(self):
        got = {t: u["billable_tokens"] for t, u in self.usage.items()}
        self.assertEqual(got, {
            "t-acme": 1800, "t-bolt": 14700, "t-cove": 1700, "t-dune": 30000, "t-echo": 0,
            "t-fern": 2400, "t-gale": 16700, "t-hive": 500, "t-iris": 1000, "t-jade": 6000,
        })

    def test_by_endpoint(self):
        self.maxDiff = None
        got = {t: u["by_endpoint"] for t, u in self.usage.items()}
        self.assertEqual(got, {
            "t-acme": {"/v1/chat": 3, "/v1/embed": 2},
            "t-bolt": {"/v1/chat": 5, "/v1/embed": 2},
            "t-cove": {"/v1/chat": 2, "/v1/embed": 1},
            "t-dune": {"/v1/chat": 3, "/v1/embed": 1},
            "t-echo": {},
            "t-fern": {"/v1/embed": 4},
            "t-gale": {"/v1/chat": 4, "/v1/embed": 1},
            "t-hive": {"/v1/chat": 1, "/v1/embed": 1},
            "t-iris": {"/v1/chat": 1},
            "t-jade": {"/v1/chat": 1},
        })


if __name__ == "__main__":
    unittest.main()
