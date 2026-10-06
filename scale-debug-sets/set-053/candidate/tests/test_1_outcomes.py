import unittest

from prelabelqa.reports import build_report


class TestOutcomes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.outcomes = build_report()["outcomes"]

    def test_datasets(self):
        self.assertEqual(sorted(self.outcomes), ["street", "warehouse"])

    def test_every_prelabel_has_an_outcome(self):
        self.assertEqual(sum(len(v) for v in self.outcomes.values()), 15)

    def test_street_outcomes(self):
        self.assertEqual(self.outcomes["street"], {
            "img-01/B1": "accepted",
            "img-01/B2": "accepted",
            "img-02/B3": "accepted",
            "img-02/B4": "relabeled",
            "img-03/B5": "accepted",
            "img-03/B6": "accepted",
            "img-04/B7": "adjusted",
            "img-09/B15": "accepted",
        })

    def test_warehouse_outcomes(self):
        self.assertEqual(self.outcomes["warehouse"], {
            "img-05/B8": "adjusted",
            "img-05/B9": "accepted",
            "img-06/B10": "deleted",
            "img-06/B11": "adjusted",
            "img-07/B12": "accepted",
            "img-08/B13": "relabeled",
            "img-08/B14": "accepted",
        })


if __name__ == "__main__":
    unittest.main()
