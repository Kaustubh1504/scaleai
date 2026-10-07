import unittest
from datetime import datetime

from ticketflow.reports import build_report


def at(hm):
    h, m = map(int, hm.split(":"))
    return datetime(2026, 5, 4, h, m)


class TestReplay(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()
        cls.tickets = cls.report["tickets"]

    def refused(self, *ids):
        return [r for r in self.report["rejected"] if r[1] in ids]

    def test_lead_resolution(self):
        t03 = self.tickets["T03"]
        self.assertEqual((t03["state"], t03["updated_at"]), ("closed", at("11:30")))
        self.assertEqual(self.refused("T03"), [])

    def test_agent_handoff(self):
        t09 = self.tickets["T09"]
        self.assertEqual((t09["state"], t09["updated_at"]), ("resolved", at("13:30")))
        self.assertEqual(self.refused("T09"), [])

    def test_final_states(self):
        states = {tid: t["state"] for tid, t in self.tickets.items() if tid not in ("T03", "T09")}
        self.assertEqual(states, {
            "T01": "closed", "T02": "waiting_customer", "T04": "triaged",
            "T05": "in_progress", "T06": "waiting_customer", "T07": "new",
            "T08": "waiting_customer", "T10": "awaiting_approval", "T11": "waiting_customer",
            "T12": "waiting_customer", "T13": "waiting_customer", "T14": "waiting_customer",
        })
        self.assertEqual(self.tickets["T10"]["updated_at"], at("14:50"))
        self.assertIsNone(self.tickets["T07"]["updated_at"])

    def test_other_refusals(self):
        self.assertEqual(self.refused("T99", "T01", "T04", "T06", "T08"), [
            ["12:00", "T99", "ana", "reply", "unknown_ticket"],
            ["12:00", "T06", "closer-bot", "close", "invalid_transition"],
            ["12:05", "T08", "initech", "reply", "role_not_allowed"],
            ["12:30", "T01", "ana", "tag", "invalid_transition"],
            ["13:10", "T04", "temp1", "triage", "role_not_allowed"],
        ])


if __name__ == "__main__":
    unittest.main()
