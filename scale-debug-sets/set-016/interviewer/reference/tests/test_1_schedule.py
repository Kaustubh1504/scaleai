import unittest

from nightshift.reports import build_report

EXPECTED_ROUNDS = [
    ["J05", "J02"],
    ["J01", "J03"],
    ["J04", "J03"],
    ["J06", "J08"],
    ["J08", "J07"],
    ["J07", "J11"],
    ["J14"],
]


class TestSchedule(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_first_round(self):
        self.assertEqual(self.report["rounds"][0], ["J05", "J02"])

    def test_disabled_jobs_never_run(self):
        ran = {jid for batch in self.report["rounds"] for jid in batch}
        self.assertEqual(ran & {"J12", "J13"}, set())
        self.assertNotIn("J12", self.report["jobs"])
        self.assertNotIn("J13", self.report["jobs"])

    def test_all_rounds(self):
        self.maxDiff = None
        self.assertEqual(self.report["rounds"], EXPECTED_ROUNDS)


if __name__ == "__main__":
    unittest.main()
