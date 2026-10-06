import unittest

from spanmerge.report import build_report


class TestSpans(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_misaligned(self):
        self.assertEqual(self.report["misaligned"], [("d01", "ann-b", "Boston"), ("d01", "ann-c", "Acme Corp")])

    def test_kept_span_counts(self):
        got = {a: sum(len(v) for v in docs.values()) for a, docs in self.report["kept"].items()}
        self.assertEqual(got, {"ann-a": 14, "ann-b": 11, "ann-c": 9})

    def test_overlaps_resolved(self):
        self.assertEqual(self.report["kept"]["ann-c"]["d10"], [[0, 18, "ORG"]])
        self.assertEqual(self.report["kept"]["ann-a"]["d10"], [[0, 5, "ORG"], [10, 18, "ORG"]])


if __name__ == "__main__":
    unittest.main()
