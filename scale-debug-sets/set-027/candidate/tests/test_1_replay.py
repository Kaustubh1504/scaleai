import unittest

from leasebeat.reports import build_report


class TestReplay(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_dispatch_log(self):
        self.assertEqual(self.report["dispatch"], [
            ["08:00:00", "w1", "T08"], ["08:00:05", "w2", "T02"], ["08:00:10", "w3", "T04"],
            ["08:00:40", "w1", "T05"], ["08:01:30", "w3", "T10"], ["08:03:00", "w1", "T02"],
            ["08:03:10", "w2", "T01"], ["08:03:20", "w3", "T07"], ["08:03:30", "w4", "T03"],
            ["08:04:40", "w3", "T07"], ["08:05:00", "w4", "T06"], ["08:05:30", "w5", "T09"],
            ["08:05:50", "w5", None],
        ])

    def test_heartbeats(self):
        self.assertEqual(self.report["heartbeats"], [
            ["08:00:50", "w2", "T02", "ok"],
            ["08:01:20", "w1", "T05", "ok"],
            ["08:01:50", "w2", "T02", "rejected"],
            ["08:02:10", "w3", "T10", "ok"],
            ["08:04:15", "w4", "T03", "ok"],
        ])

    def test_rejected_acks(self):
        self.assertEqual(self.report["rejected_acks"], [["08:03:05", "w2", "T02"], ["08:06:20", "w3", "T07"]])

    def test_final_state(self):
        self.assertEqual(self.report["dead_letter"], ["T06", "T07"])
        self.assertEqual({t: n for t, n in self.report["attempts"].items() if n != 1}, {"T02": 2, "T07": 2})


if __name__ == "__main__":
    unittest.main()
