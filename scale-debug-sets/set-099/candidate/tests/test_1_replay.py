import unittest

from leasehold.reports import build_report


class TestReplay(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_dispatch(self):
        self.assertEqual(self.report["dispatch"], [
            ["08:00:00", "w01", "K02"], ["08:00:30", "w03", "K03"], ["08:01:00", "w05", "K12"],
            ["08:01:10", "w02", "K05"], ["08:02:30", "w10", "K12"], ["08:03:00", "w04", "K11"],
            ["08:03:30", "w02", "K07"], ["08:04:30", "w08", "K01"], ["08:05:40", "w09", "K08"],
            ["08:06:00", "w11", "K07"], ["08:07:00", "w05", "K06"], ["08:07:30", "w01", "K07"],
            ["08:08:30", "w07", "K06"], ["08:10:30", "w10", "K09"], ["08:11:10", "w02", "K10"],
            ["08:12:30", "w03", "K04"],
        ])

    def test_expired_leases(self):
        self.assertEqual(self.report["expired"], [
            ["08:02:30", "w05", "K12"], ["08:02:30", "w02", "K05"], ["08:05:40", "w02", "K07"],
            ["08:08:30", "w05", "K06"], ["08:09:40", "w01", "K07"], ["08:12:00", "w10", "K09"],
            ["12:00:00", "w03", "K04"],
        ])

    def test_rejected_events(self):
        self.assertEqual(self.report["rejected"], [
            ["08:01:40", "w06", "claim", None, "unknown_worker"],
            ["08:02:40", "w05", "ack", "K12", "not_holder"],
            ["08:04:00", "w01", "ack", "K02", "closed"],
            ["08:06:20", "w02", "nack", "K07", "not_holder"],
            ["08:07:10", "w12", "claim", None, "unknown_worker"],
            ["08:07:40", "w05", "ack", "K99", "unknown_task"],
            ["08:09:40", "w01", "ack", "K07", "closed"],
            ["08:12:00", "w10", "heartbeat", "K09", "not_holder"],
        ])

    def test_final_status(self):
        self.assertEqual(self.report["status"], {
            "K01": "done", "K02": "done", "K03": "done", "K04": "pending", "K05": "dead", "K06": "done",
            "K07": "dead", "K08": "done", "K09": "pending", "K10": "done", "K11": "done", "K12": "done",
        })


if __name__ == "__main__":
    unittest.main()
