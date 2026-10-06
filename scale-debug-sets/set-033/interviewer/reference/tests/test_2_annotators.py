import unittest

from spanmerge.reports import build_report


class TestAnnotators(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.annotators = build_report()["annotators"]

    def test_annotators_listed(self):
        self.assertEqual(sorted(self.annotators), ["a01", "a02", "a03", "a04", "a05", "a06"])

    def test_invalid_counts(self):
        got = {a: r["invalid"] for a, r in self.annotators.items()}
        self.assertEqual(got, {"a01": 1, "a02": 1, "a03": 0, "a04": 1, "a05": 0, "a06": 0})

    def test_agreement(self):
        got = {a: r["agreement"] for a, r in self.annotators.items()}
        self.assertEqual(got, {"a01": 1.0, "a02": 0.75, "a03": 1.0, "a04": 1.0, "a05": 1.0, "a06": 0.714})


if __name__ == "__main__":
    unittest.main()
