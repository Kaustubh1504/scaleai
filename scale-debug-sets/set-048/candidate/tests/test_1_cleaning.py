import unittest

from splitkit.reports import build_report


class TestCleaning(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_excluded_rows(self):
        self.assertEqual(self.report["excluded"], ["S-010", "S-036"])

    def test_duplicate_rows(self):
        self.assertEqual(self.report["duplicates"], ["S-014", "S-019"])

    def test_blank_labels_dropped(self):
        everywhere = [sid for ids in self.report["splits"].values() for sid in ids] + self.report["capped"]
        self.assertNotIn("S-035", everywhere)


if __name__ == "__main__":
    unittest.main()
