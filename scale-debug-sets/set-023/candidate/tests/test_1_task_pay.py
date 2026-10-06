import unittest

from payroll.reports import build_report


class TestTaskPay(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pay = build_report()["task_pay"]

    def test_only_accepted_known_tasks_paid(self):
        unpaid = {"T105", "T109", "T117", "T129"}
        self.assertEqual(len(self.pay), 26)
        self.assertFalse(unpaid & set(self.pay))

    def test_on_time_hourly_pay(self):
        hourly = {tid: self.pay[tid] for tid in ("T101", "T103", "T107", "T110", "T115",
                                                 "T116", "T119", "T123", "T125", "T130")}
        self.assertEqual(hourly, {
            "T101": 925, "T103": 600, "T107": 1325, "T110": 1230, "T115": 1500,
            "T116": 600, "T119": 725, "T123": 1250, "T125": 990, "T130": 1000,
        })

    def test_late_submissions(self):
        late = {tid: self.pay[tid] for tid in ("T106", "T113", "T121")}
        self.assertEqual(late, {"T106": 575, "T113": 45, "T121": 1350})


if __name__ == "__main__":
    unittest.main()
