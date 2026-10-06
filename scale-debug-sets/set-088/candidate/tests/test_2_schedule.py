import unittest

from batchsched.report import build_schedule


def lane(jobs, prefix):
    return {jid: (r["state"], r["attempts"], r["worker"], r["start"], r["end"])
            for jid, r in jobs.items() if jid.startswith(prefix)}


class TestSchedule(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.jobs = build_schedule()["jobs"]

    def test_mem_lane(self):
        self.assertEqual(lane(self.jobs, "M"), {
            "M01": ("succeeded", 1, "w08", "08:00", "08:50"),
            "M02": ("succeeded", 1, "w09", "08:00", "09:10"),
            "M03": ("succeeded", 1, "w08", "08:50", "09:20"),
            "M04": ("succeeded", 1, "w08", "09:20", "09:40"),
        })

    def test_job_after_horizon_stays_pending(self):
        self.assertEqual(lane(self.jobs, "L"), {"L01": ("pending", 0, None, None, None)})

    def test_2_cpu_lane(self):
        self.assertEqual(lane(self.jobs, "C"), {
            "C01": ("succeeded", 1, "w01", "08:20", "09:00"),
            "C02": ("succeeded", 1, "w01", "08:00", "08:20"),
            "C03": ("succeeded", 1, "w02", "08:00", "08:30"),
            "C04": ("succeeded", 1, "w02", "08:30", "08:40"),
        })

    def test_3_io_lane(self):
        self.assertEqual(lane(self.jobs, "I"), {
            "I01": ("succeeded", 2, "w06", "08:00", "08:35"),
            "I02": ("succeeded", 1, "w06", "08:35", "08:45"),
            "I03": ("succeeded", 1, "w06", "08:45", "08:55"),
        })

    def test_4_gpu_lane(self):
        self.assertEqual(lane(self.jobs, "G"), {
            "G01": ("succeeded", 1, "w04", "08:00", "08:30"),
            "G02": ("failed", 1, "w04", "08:50", "09:00"),
            "G03": ("succeeded", 1, "w04", "08:30", "08:50"),
        })


if __name__ == "__main__":
    unittest.main()
