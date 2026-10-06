import unittest

from spanmerge.reports import build_report


class TestSummary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.summary = build_report()["summary"]

    def test_named_entities(self):
        self.assertEqual(self.summary["named_entities"], 6)

    def test_docs_without_entities(self):
        self.assertEqual(self.summary["docs_without_entities"], ["D08", "D09", "D10"])

    def test_annotators(self):
        self.assertEqual(self.summary["annotators"], 5)


if __name__ == "__main__":
    unittest.main()
