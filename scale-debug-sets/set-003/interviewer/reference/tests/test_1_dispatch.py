import unittest

from leasequeue.reports import build_report

EXPECTED_DISPATCH = [
    ["2026-04-01 08:00", "w1", "A-101"],
    ["2026-04-01 08:01", "w2", "A-103"],
    ["2026-04-01 08:06", "w3", "A-110"],
    ["2026-04-01 08:40", "w4", "A-110"],
    ["2026-04-01 08:45", "w5", "A-106"],
    ["2026-04-01 08:50", "w1", "A-102"],
    ["2026-04-02 08:45", "w2", "A-104"],
    ["2026-04-02 08:50", "w3", "A-108"],
    ["2026-04-02 09:22", "w1", "A-108"],
    ["2026-04-02 09:35", "w5", "A-109"],
]


class TestDispatch(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_first_lease_gets_most_urgent_task(self):
        self.assertEqual(self.report["dispatch"][0], ["2026-04-01 08:00", "w1", "A-101"])

    def test_priority_tie_goes_to_older_task(self):
        day_one = [row[2] for row in self.report["dispatch"] if row[0].startswith("2026-04-01")]
        self.assertLess(day_one.index("A-106"), day_one.index("A-102"))

    def test_dispatch_log(self):
        self.maxDiff = None
        self.assertEqual(self.report["dispatch"], EXPECTED_DISPATCH)


if __name__ == "__main__":
    unittest.main()
