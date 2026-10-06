import unittest

from relaymesh.report import build_report


def zone_slice(assignments, prefix):
    return {rid: wid for rid, wid in assignments.items() if rid.startswith(prefix)}


class TestRouting(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.assignments = build_report()["assignments"]

    def test_every_request_has_an_outcome(self):
        self.assertEqual(len(self.assignments), 31)

    def test_central_assignments(self):
        self.assertEqual(zone_slice(self.assignments, "c"), {
            "c01": "cen-1", "c02": "cen-2", "c03": "cen-3", "c04": "cen-1", "c05": "cen-1",
            "c06": "cen-2", "c07": "cen-1", "c08": "cen-1", "c09": "cen-2", "c10": "cen-3",
        })

    def test_1_east_assignments(self):
        self.assertEqual(zone_slice(self.assignments, "e"), {
            "e01": "east-1", "e02": "east-2", "e03": "east-3", "e04": "east-1",
            "e05": "east-1", "e06": "east-2", "e07": "east-1", "e08": "east-2",
        })

    def test_2_west_assignments(self):
        self.assertEqual(zone_slice(self.assignments, "w"), {
            "w01": "west-1", "w02": "west-1", "w03": "west-2",
            "w04": "west-1", "w05": "west-1", "w06": "west-1",
        })


if __name__ == "__main__":
    unittest.main()
