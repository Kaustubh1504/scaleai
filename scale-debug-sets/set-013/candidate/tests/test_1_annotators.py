import unittest

from fraudscan.reports import build_report


def row(submissions, fast_ratio, *flags):
    return {"submissions": submissions, "fast_ratio": fast_ratio, "flags": list(flags)}


EXPECTED = {
    "ann-01": row(3, 0.0),
    "ann-02": row(4, 0.75, "speeding"),
    "ann-03": row(2, 0.0, "copying"),
    "ann-04": row(4, 0.5, "speeding"),
    "ann-05": row(2, 0.0, "copying"),
    "ann-06": row(3, 0.0),
    "ann-07": row(2, 0.0),
    "ann-08": row(3, 0.0, "copying"),
    "ann-09": row(2, 0.5, "speeding"),
    "ann-10": row(2, 0.0),
}


class TestAnnotators(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.annotators = build_report()["annotators"]

    def test_unknown_annotators_ignored(self):
        self.assertNotIn("ann-11", self.annotators)

    def test_exactly_twenty_seconds_is_not_fast(self):
        self.assertEqual(self.annotators["ann-07"]["fast_ratio"], 0.0)

    def test_annotator_table(self):
        self.maxDiff = None
        self.assertEqual(self.annotators, EXPECTED)


if __name__ == "__main__":
    unittest.main()
