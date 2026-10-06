import unittest

from jobsim.reports import build_report


class TestJobs(unittest.TestCase):
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_statuses(self):
        statuses = {k: v["status"] for k, v in self.report["jobs"].items() if k != "b1"}
        self.assertEqual(statuses, {
            "a1": "succeeded", "a2": "succeeded", "a3": "succeeded", "a4": "failed", "a5": "skipped",
            "a6": "succeeded", "a9": "succeeded", "b2": "blocked", "c1": "blocked", "c2": "blocked",
            "c3": "skipped", "m1": "succeeded", "m2": "succeeded", "m3": "succeeded", "m4": "succeeded",
            "m5": "succeeded", "m6": "succeeded",
        })

    def test_blocked(self):
        self.assertEqual(self.report["blocked"], {
            "b1": "missing_dep:zz-missing", "b2": "missing_dep:ghost", "c1": "cycle", "c2": "cycle",
        })
        self.assertEqual(self.report["jobs"]["b1"]["status"], "blocked")

    def test_event_log(self):
        events = self.report["events"]
        self.assertEqual(events["m5"], ["start@07:00/w1", "fail@07:20", "start@07:35/w1", "done@07:55"])
        self.assertEqual(events["a4"], ["start@14:30/w1", "fail@14:40"])


if __name__ == "__main__":
    unittest.main()
