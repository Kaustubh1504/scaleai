import unittest

from ratingpanel.reports import build_report


class TestCleaning(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_registry_annotators_only(self):
        self.assertEqual(sorted(self.report["annotators"]), [f"ann-{n:02d}" for n in range(1, 11)])

    def test_1_rushed_counts(self):
        rushed = {aid: row["rushed"] for aid, row in self.report["annotators"].items() if row["rushed"]}
        self.assertEqual(rushed, {"ann-08": 1, "ann-10": 1})

    def test_2_resubmitted_item(self):
        self.assertEqual(self.report["items"]["I-04"],
                         {"status": "agreed", "consensus": 7, "agreement": 1.0})


if __name__ == "__main__":
    unittest.main()
