import unittest

from crew.reports import build_report


class TestAllocations(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_top_priority_projects(self):
        top = {pid: self.report["allocations"][pid] for pid in ("P02", "P03", "P07")}
        self.assertEqual(top, {
            "P02": {"C10": 6, "C04": 14},
            "P03": {"C02": 10, "C03": 10},
            "P07": {},
        })

    def test_all_allocations(self):
        self.maxDiff = None
        self.assertEqual(self.report["allocations"], {
            "P01": {"C08": 8, "C01": 20, "C12": 2},
            "P02": {"C10": 6, "C04": 14},
            "P03": {"C02": 10, "C03": 10},
            "P04": {},
            "P05": {"C03": 10, "C09": 5},
            "P06": {"C05": 10},
            "P07": {},
            "P08": {"C04": 1},
            "P09": {},
            "P10": {"C12": 3, "C09": 5, "C05": 4},
        })

    def test_unfilled(self):
        self.assertEqual(self.report["unfilled"], {"P04": 10, "P08": 9, "P09": 8})


if __name__ == "__main__":
    unittest.main()
