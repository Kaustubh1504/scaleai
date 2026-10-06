import unittest

from splitkit.reports import build_report


class TestCleaning(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dropped = build_report()["dropped"]

    def test_unlabeled_rows(self):
        self.assertEqual(self.dropped["unlabeled"], ["I009", "I034"])

    def test_excluded_rows(self):
        self.assertEqual(self.dropped["excluded"], ["I013", "I018", "I022", "I026"])

    def test_duplicate_rows(self):
        self.assertEqual(self.dropped["duplicate"], ["I012", "I030"])


if __name__ == "__main__":
    unittest.main()
