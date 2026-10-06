import unittest

from nightshift.report import build_report


class TestJobs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.jobs = build_report()["jobs"]

    def test_etl_and_ops_all_done(self):
        statuses = {jid: r["status"] for jid, r in self.jobs.items() if r["queue"] in ("etl", "ops")}
        self.assertEqual(set(statuses.values()), {"done"})
        self.assertEqual(len(statuses), 9)

    def test_3_reports_dependencies(self):
        got = {jid: (r["status"], r["first_start"], r["finished"])
               for jid, r in self.jobs.items() if r["queue"] == "reports"}
        self.assertEqual(got, {
            "rpt-1": ("done", "00:00", "00:45"),
            "rpt-2": ("done", "00:45", "01:00"),
            "rpt-3": ("done", "00:30", "00:50"),
            "rpt-4": ("done", "00:50", "01:00"),
        })

    def test_4_ops_wait_minutes(self):
        got = {jid: r["wait_min"] for jid, r in self.jobs.items() if r["queue"] == "ops"}
        self.assertEqual(got, {"ops-1": 1590, "ops-2": 50, "ops-3": 0, "ops-4": 20})


if __name__ == "__main__":
    unittest.main()
