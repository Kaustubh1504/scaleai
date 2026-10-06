import unittest

from sftpack.reports import build_report


class TestSummary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.summary = build_report()["summary"]

    def test_sources(self):
        self.assertEqual(self.summary["sources"], ["vendor-a", "vendor-b", "vendor-c"])

    def test_longest_example(self):
        self.assertEqual(self.summary["longest_example"], "c05")

    def test_3_tag_counts(self):
        self.assertEqual(self.summary["tag_counts"], {
            "chat": 3, "code": 3, "long": 1, "math": 3, "python": 1, "safety": 1,
        })


if __name__ == "__main__":
    unittest.main()
