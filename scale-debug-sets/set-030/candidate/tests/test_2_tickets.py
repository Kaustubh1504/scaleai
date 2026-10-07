import unittest

from ticketflow.reports import build_report


class TestTickets(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tickets = build_report()["tickets"]

    def test_labels(self):
        labels = {tid: self.tickets[tid]["labels"] for tid in ("T01", "T02", "T06", "T10")}
        self.assertEqual(labels, {"T01": ["billing"], "T02": ["login"], "T06": ["outage"], "T10": []})

    def test_first_response_after_triage(self):
        got = {tid: self.tickets[tid]["first_response_min"] for tid in ("T02", "T04", "T12", "T14")}
        self.assertEqual(got, {"T02": 55.0, "T04": None, "T12": 180.0, "T14": 30.0})

    def test_first_response_direct(self):
        got = {tid: self.tickets[tid]["first_response_min"] for tid in ("T01", "T03", "T05", "T07", "T08", "T11", "T13")}
        self.assertEqual(got, {"T01": 30.0, "T03": 15.0, "T05": 20.0, "T07": None,
                               "T08": 30.0, "T11": 120.0, "T13": 40.0})


if __name__ == "__main__":
    unittest.main()
