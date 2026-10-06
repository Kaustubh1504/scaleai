import unittest

from spanmerge.reports import build_report


class TestAdjudication(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.docs = build_report()["documents"]

    def test_legacy_tool_offsets(self):
        self.assertEqual(self.docs["D04"], [
            [13, 18, "LOC", "Paris"],
            [22, 26, "LOC", "Lima"],
            [37, 44, "DATE", "12 June"],
        ])

    def test_overlapping_spans(self):
        self.assertEqual(self.docs["D02"], [
            [4, 18, "ORG", "Morgan Stanley"],
            [29, 35, "LOC", "Boston"],
            [46, 50, "DATE", "2019"],
        ])

    def test_other_documents(self):
        others = {d: ents for d, ents in self.docs.items() if d not in ("D02", "D04")}
        self.assertEqual(others, {
            "D01": [[0, 12, "PER", "Alice Moreno"], [33, 39, "LOC", "Denver"]],
            "D03": [[4, 14, "PER", "Priya Shah"], [45, 51, "DATE", "Friday"]],
            "D05": [[0, 6, "ORG", "Globex"], [13, 22, "PER", "Tom Reyes"]],
            "D06": [[24, 28, "LOC", "Oslo"]],
            "D07": [[0, 8, "PER", "Hana Kim"]],
            "D08": [],
            "D09": [],
            "D10": [],
        })


if __name__ == "__main__":
    unittest.main()
