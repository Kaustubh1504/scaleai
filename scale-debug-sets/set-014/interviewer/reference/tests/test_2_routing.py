import unittest

from lbsim.reports import build_report


class TestRouting(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_no_rejections(self):
        self.assertEqual(self.report["rejected"], [])

    def test_blank_duration_not_routed(self):
        self.assertNotIn("R13", self.report["assignments"])

    def test_3_assignments(self):
        self.maxDiff = None
        self.assertEqual(self.report["assignments"], {
            "R01": "W-04", "R02": "W-01", "R03": "W-06", "R04": "W-09", "R05": "W-03",
            "R06": "W-10", "R07": "W-09", "R08": "W-06", "R09": "W-04", "R10": "W-06",
            "R11": "W-09", "R12": "W-04", "R14": "W-01", "R15": "W-06", "R16": "W-09",
            "R17": "W-01", "R18": "W-05", "R19": "W-04", "R20": "W-09",
        })

    def test_4_peak_in_flight(self):
        self.assertEqual(self.report["peak_in_flight"], 5)


if __name__ == "__main__":
    unittest.main()
