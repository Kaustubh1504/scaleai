import unittest

from batchsched.report import build_schedule


class TestReport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_schedule()["report"]

    def test_makespan(self):
        self.assertEqual(self.report["makespan_minutes"], 100)

    def test_busy_minutes(self):
        pools = self.report["pools"]
        self.assertEqual((pools["cpu"]["busy_minutes"], pools["mem"]["busy_minutes"]), (100, 170))

    def test_5_longest_wait(self):
        self.assertEqual(self.report["longest_wait"], {"job": "M01", "minutes": 2890})

    def test_6_pool_capacity(self):
        pools = self.report["pools"]
        self.assertEqual({p: row["slots"] for p, row in pools.items()}, {"cpu": 2, "gpu": 1, "io": 1, "mem": 2})
        self.assertEqual((pools["cpu"]["utilization"], pools["mem"]["utilization"]), (50.0, 85.0))


if __name__ == "__main__":
    unittest.main()
