import unittest

from crewplan.reports import build_report

EXPECTED = {
    "P01": ["K02", "K03"],
    "P02": ["K04"],
    "P03": ["K09", "K13"],
    "P04": ["K13", "K03", "K07"],
    "P05": ["K06"],
    "P06": [],
    "P07": [],
    "P08": ["K01"],
    "P09": ["K11", "K08"],
    "P10": [],
    "P11": ["K03", "K07"],
    "P12": [],
}


class TestStaffing(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_assignments(self):
        self.maxDiff = None
        self.assertEqual(self.report["assignments"], EXPECTED)

    def test_open_seats(self):
        self.assertEqual(self.report["open_seats"], {"P05": 1})


if __name__ == "__main__":
    unittest.main()
