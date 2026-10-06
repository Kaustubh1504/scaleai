import unittest

from nightshift.report import build_report


def timeline(jobs, queue):
    return {jid: (r["first_start"], r["finished"]) for jid, r in jobs.items() if r["queue"] == queue}


class TestDispatch(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.jobs = build_report()["jobs"]

    def test_every_job_reported(self):
        self.assertEqual(len(self.jobs), 16)
        self.assertEqual(
            sorted({r["queue"] for r in self.jobs.values()}), ["etl", "ops", "reports", "training"]
        )

    def test_1_etl_schedule(self):
        self.assertEqual(timeline(self.jobs, "etl"), {
            "etl-1": ("00:45", "01:15"),
            "etl-2": ("00:00", "00:20"),
            "etl-3": ("01:25", "01:40"),
            "etl-4": ("00:20", "00:45"),
            "etl-5": ("01:15", "01:25"),
        })

    def test_ops_schedule(self):
        self.assertEqual(timeline(self.jobs, "ops"), {
            "ops-1": ("00:00", "00:40"),
            "ops-2": ("00:40", "01:10"),
            "ops-3": ("01:30", "02:30"),
            "ops-4": ("01:50", "02:10"),
        })
        self.assertEqual(self.jobs["ops-3"]["attempts"], 2)

    def test_2_training_outcomes(self):
        got = {jid: (r["status"], r["attempts"], r["finished"])
               for jid, r in self.jobs.items() if r["queue"] == "training"}
        self.assertEqual(got, {
            "trn-1": ("done", 3, "03:40"),
            "trn-2": ("done", 1, "04:10"),
            "trn-3": ("done", 1, "01:20"),
        })


if __name__ == "__main__":
    unittest.main()
