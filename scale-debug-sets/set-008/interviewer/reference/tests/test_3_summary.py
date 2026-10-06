import unittest

from rosterload.report import build_report


class TestSummary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.summary = build_report()["summary"]

    def test_accepted_by_vendor(self):
        self.assertEqual(self.summary["accepted_by_vendor"], {"vendor_a": 3, "vendor_b": 6, "vendor_c": 7})

    def test_duplicates_merged(self):
        self.assertEqual(self.summary["duplicates_merged"], 6)

    def test_rejected_by_reason(self):
        self.assertEqual(self.summary["rejected_by_reason"], {"invalid_value": 5, "missing_field": 3})

    def test_countries(self):
        self.assertEqual(self.summary["countries"],
                         {"CA": 1, "GB": 4, "IN": 3, "SE": 1, "UNKNOWN": 1, "US": 6})


if __name__ == "__main__":
    unittest.main()
