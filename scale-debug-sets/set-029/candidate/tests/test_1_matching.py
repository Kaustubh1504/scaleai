import unittest

from boxaudit.reports import build_report


class TestMatching(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_unmatched_predictions(self):
        unmatched = sorted({f"p{n:02d}" for n in range(1, 23)} - set(self.report["matches"]))
        self.assertEqual(unmatched, ["p07", "p09", "p12", "p14", "p20"])

    def test_matches(self):
        self.assertEqual(self.report["matches"], {
            "p01": "g01", "p02": "g02", "p03": "g01",
            "p04": "g03", "p05": "g04", "p06": "g03", "p08": "g03",
            "p10": "g05", "p11": "g06", "p13": "g06", "p15": "g06",
            "p16": "g07", "p17": "g07", "p18": "g08", "p19": "g08",
            "p21": "g09", "p22": "g09",
        })


if __name__ == "__main__":
    unittest.main()
