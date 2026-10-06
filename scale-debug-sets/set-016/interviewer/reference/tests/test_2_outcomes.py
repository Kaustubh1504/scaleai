import unittest

from nightshift.reports import build_report


def job(status, attempts, finished_round):
    return {"status": status, "attempts": attempts, "finished_round": finished_round}


EXPECTED_JOBS = {
    "J01": job("succeeded", 1, 2),
    "J02": job("succeeded", 1, 1),
    "J03": job("succeeded", 2, 3),
    "J04": job("succeeded", 1, 3),
    "J05": job("dead", 1, 1),
    "J06": job("succeeded", 1, 4),
    "J07": job("dead", 2, 6),
    "J08": job("succeeded", 2, 5),
    "J09": job("skipped", 0, None),
    "J10": job("skipped", 0, None),
    "J11": job("succeeded", 1, 6),
    "J14": job("succeeded", 1, 7),
}


class TestOutcomes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.jobs = build_report()["jobs"]

    def test_dead_jobs(self):
        dead = sorted(jid for jid, j in self.jobs.items() if j["status"] == "dead")
        self.assertEqual(dead, ["J05", "J07"])

    def test_dependents_of_dead_jobs_skipped(self):
        self.assertEqual({jid: self.jobs[jid]["status"] for jid in ("J09", "J10")},
                         {"J09": "skipped", "J10": "skipped"})

    def test_attempts(self):
        self.assertEqual({jid: j["attempts"] for jid, j in self.jobs.items()},
                         {jid: j["attempts"] for jid, j in EXPECTED_JOBS.items()})

    def test_all_jobs(self):
        self.maxDiff = None
        self.assertEqual(self.jobs, EXPECTED_JOBS)


if __name__ == "__main__":
    unittest.main()
