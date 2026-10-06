import unittest

from podstaff.reports import build_report


class TestAssignment(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.assignments = build_report()["assignments"]

    def test_every_project_listed(self):
        self.assertEqual(sorted(self.assignments), [f"P{n:02d}" for n in range(1, 11)])
        self.assertEqual(self.assignments["P04"], [])

    def test_top_priority_projects(self):
        self.assertEqual(self.assignments["P01"], ["C01", "C02", "C03"])
        self.assertEqual(self.assignments["P03"], ["C01", "C02"])

    def test_chat_safety(self):
        self.assertEqual(self.assignments["P02"], ["C01", "C10"])

    def test_spanish_qa(self):
        self.assertEqual(self.assignments["P05"], ["C03", "C16"])

    def test_remaining_projects(self):
        self.assertEqual({p: self.assignments[p] for p in ("P06", "P07", "P08", "P09", "P10")}, {
            "P06": ["C14", "C06"],
            "P07": ["C15"],
            "P08": ["C13", "C11"],
            "P09": ["C03"],
            "P10": ["C14", "C15", "C08"],
        })


if __name__ == "__main__":
    unittest.main()
