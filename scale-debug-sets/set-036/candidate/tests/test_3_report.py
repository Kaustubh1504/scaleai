import unittest

from tests.helpers import run_against_mock


class TestReport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server, cls.waits, cls.report = run_against_mock()
        cls.summary = cls.report["summary"]

    @classmethod
    def tearDownClass(cls):
        cls.server.stop()

    def test_counts(self):
        self.assertEqual((self.summary["documents"], self.summary["embedded"], self.summary["total_tokens"]),
                         (18, 14, 208))

    def test_tokens_per_doc(self):
        self.assertEqual(self.summary["tokens_per_doc"], 14.86)

    def test_near_duplicates(self):
        self.assertEqual(self.summary["near_duplicates"], [
            ["d03", "d13", 1.0],
            ["d05", "d14", 0.98],
        ])


if __name__ == "__main__":
    unittest.main()
