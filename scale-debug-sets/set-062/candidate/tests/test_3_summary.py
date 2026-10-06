import unittest

from relaymesh.report import build_report


class TestSummary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.summary = build_report()["summary"]

    def test_requests_by_zone(self):
        self.assertEqual(
            self.summary["requests_by_zone"],
            {"central": 10, "east": 8, "north": 6, "south": 1, "west": 6},
        )

    def test_5_rejected(self):
        self.assertEqual(self.summary["rejected"], ["n02", "n06", "s01"])

    def test_6_out_of_rotation(self):
        self.assertEqual(self.summary["out_of_rotation"], ["cen-4", "east-3", "west-2", "west-3"])


if __name__ == "__main__":
    unittest.main()
