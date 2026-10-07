import json
import unittest
from datetime import datetime

from ticketflow.reports import build_report, to_json


class TestReport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_sla_breaches(self):
        self.assertEqual(self.report["sla_breaches"], ["T05", "T07", "T13"])

    def test_actor_activity(self):
        self.assertEqual(self.report["actors"], {
            "acme": {"customer_reply": 2},
            "ana": {"reply": 5, "resolve": 1, "tag": 3, "triage": 1},
            "bo": {"reply": 5, "resolve": 1, "start": 1, "tag": 1, "triage": 3},
            "closer-bot": {"close": 3},
            "globex": {"customer_reply": 2},
            "initech": {"reply": 1},
            "lee": {"reply": 1, "resolve": 1},
            "mira": {"approve": 2, "reply": 1, "tag": 1},
            "noor": {"resolve": 1, "start": 1, "triage": 1},
            "temp1": {"triage": 1},
        })

    def test_json_output(self):
        self.assertEqual(self.report["as_of"], datetime(2026, 5, 4, 18, 0))
        data = json.loads(to_json(self.report))
        self.assertEqual(data["as_of"], "2026-05-04T18:00:00")
        self.assertEqual(sorted(data["tickets"]), [f"T{n:02d}" for n in range(1, 15)])
        self.assertEqual(data["tickets"]["T07"]["updated_at"], None)


if __name__ == "__main__":
    unittest.main()
