import unittest

from jobsim.reports import build_report


def run(start, end, worker, attempts=1):
    return {"status": "succeeded", "attempts": attempts, "start": start, "end": end, "worker": worker}


class TestSchedule(unittest.TestCase):
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        cls.jobs = build_report()["jobs"]

    def slice(self, ids):
        return {job_id: self.jobs[job_id] for job_id in ids}

    def test_morning_wave(self):
        self.assertEqual(self.slice(["m1", "m2", "m3", "m4", "m6"]), {
            "m1": run("06:00", "07:00", "w1"),
            "m2": run("06:00", "06:45", "w2"),
            "m3": run("06:45", "07:15", "w2"),
            "m4": run("07:15", "07:45", "w2"),
            "m6": run("07:20", "07:35", "w1"),
        })

    def test_afternoon_wave(self):
        self.assertEqual(self.slice(["a9", "a1", "a3", "a2", "a6"]), {
            "a9": run("13:00", "14:00", "w1"),
            "a1": run("13:02", "13:42", "w2"),
            "a3": run("13:42", "14:12", "w2"),
            "a2": run("14:00", "14:30", "w1"),
            "a6": run("14:12", "14:32", "w2"),
        })

    def test_retries(self):
        self.assertEqual(self.jobs["m5"], run("07:35", "07:55", "w1", attempts=2))
        self.assertEqual(self.jobs["a4"], {"status": "failed", "attempts": 1, "start": "14:30", "end": "14:40",
                                           "worker": "w1"})


if __name__ == "__main__":
    unittest.main()
