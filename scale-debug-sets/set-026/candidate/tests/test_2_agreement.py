import unittest

from tonevote.reports import build_report


class TestAgreement(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.annotators = build_report()["annotators"]

    def test_annotators_listed(self):
        self.assertEqual(sorted(self.annotators),
                         ["a01", "a02", "a03", "a04", "a05", "a06", "a07", "a08", "a09", "a10", "a11"])

    def test_skip_counts(self):
        skips = {aid: row["skips"] for aid, row in self.annotators.items() if row["skips"]}
        self.assertEqual(skips, {"a02": 1, "a06": 1, "a08": 2})

    def test_agreement_rates(self):
        self.maxDiff = None
        rows = {aid: self.annotators[aid] for aid in
                ("a01", "a02", "a03", "a04", "a05", "a06", "a07", "a08", "a09")}
        self.assertEqual(rows, {
            "a01": {"agreed_tasks": 6, "agreement": 1.0, "skips": 0},
            "a02": {"agreed_tasks": 5, "agreement": 0.8, "skips": 1},
            "a03": {"agreed_tasks": 5, "agreement": 0.8, "skips": 0},
            "a04": {"agreed_tasks": 3, "agreement": 0.667, "skips": 0},
            "a05": {"agreed_tasks": 4, "agreement": 0.75, "skips": 0},
            "a06": {"agreed_tasks": 4, "agreement": 1.0, "skips": 1},
            "a07": {"agreed_tasks": 4, "agreement": 0.75, "skips": 0},
            "a08": {"agreed_tasks": 4, "agreement": 0.5, "skips": 2},
            "a09": {"agreed_tasks": 2, "agreement": 1.0, "skips": 0},
        })

    def test_low_and_unscored_annotators(self):
        self.assertEqual(self.annotators["a10"], {"agreed_tasks": 4, "agreement": 0.0, "skips": 0})
        self.assertEqual(self.annotators["a11"], {"agreed_tasks": 0, "agreement": None, "skips": 0})


if __name__ == "__main__":
    unittest.main()
