import unittest

from leasebook.reports import build_report

EXPECTED_CLAIMS = [
    ["2026-06-01 09:00", "alice", "ingest", "T01"],
    ["2026-06-01 09:00", "bob", "ingest", "T02"],
    ["2026-06-01 09:01", "cara", "review", "T04"],
    ["2026-06-01 09:13", "bob", "ingest", "T02"],
    ["2026-06-01 09:22", "dan", "review", "T04"],
    ["2026-06-01 09:26", "erin", "ingest", "T01"],
    ["2026-06-01 09:30", "bob", "ingest", "T02"],
    ["2026-06-01 09:40", "cara", "review", "T05"],
    ["2026-06-01 09:42", "frank", "review", "T06"],
    ["2026-06-01 09:52", "frank", "export", "T07"],
    ["2026-06-01 10:00", "gina", "export", "T09"],
    ["2026-06-01 10:20", "alice", "review", "T06"],
    ["2026-06-01 10:20", "bob", "export", "T09"],
    ["2026-06-01 10:21", "cara", "export", "T12"],
    ["2026-06-01 10:40", "gina", "ingest", "T03"],
    ["2026-06-01 11:00", "erin", "ingest", "T03"],
    ["2026-06-01 11:30", "dan", "review", "T11"],
    ["2026-06-01 11:50", "erin", "ingest", "T10"],
    ["2026-06-01 11:55", "frank", "audit", None],
]


class TestLedger(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_first_claims_follow_priority(self):
        self.assertEqual(self.report["claims"][:3], EXPECTED_CLAIMS[:3])

    def test_claims(self):
        self.maxDiff = None
        self.assertEqual(self.report["claims"], EXPECTED_CLAIMS)

    def test_status(self):
        self.assertEqual(self.report["status"], {
            "T01": "done", "T02": "dead", "T03": "done", "T04": "done",
            "T05": "done", "T06": "dead", "T07": "done", "T08": "pending",
            "T09": "done", "T10": "pending", "T11": "pending", "T12": "pending",
        })

    def test_attempts(self):
        self.assertEqual(self.report["attempts"], {
            "T01": 2, "T02": 3, "T03": 2, "T04": 2, "T05": 1, "T06": 2,
            "T07": 1, "T08": 0, "T09": 2, "T10": 1, "T11": 1, "T12": 1,
        })

    def test_rejected(self):
        self.maxDiff = None
        self.assertEqual(self.report["rejected"], [
            ["2026-06-01 09:12", "ack", "cara", "T04"],
            ["2026-06-01 09:20", "heartbeat", "alice", "T01"],
            ["2026-06-01 09:23", "ack", "bob", "T02"],
            ["2026-06-01 09:25", "ack", "alice", "T01"],
            ["2026-06-01 09:41", "ack", "bob", "T02"],
            ["2026-06-01 10:12", "ack", "gina", "T09"],
            ["2026-06-01 10:45", "ack", "gina", "T99"],
        ])


if __name__ == "__main__":
    unittest.main()
