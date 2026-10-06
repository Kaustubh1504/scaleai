import unittest

from hitlroute.reports import build_report


class TestRouting(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.routing = build_report()["routing"]

    def _reasons(self, task):
        return {i: row["reason"] for i, row in self.routing.items()
                if row["task"] == task and row["decision"] == "human_review"}

    def test_auto_accepted(self):
        auto = sorted(i for i, row in self.routing.items() if row["decision"] == "auto_accept")
        self.assertEqual(auto, ["C01", "C04", "C10", "P01", "P04", "P07", "T01", "T05", "T07"])
        self.assertEqual(len(self.routing), 28)

    def test_toxicity_review_reasons(self):
        self.assertEqual(self._reasons("toxicity"), {
            "T02": "low_confidence", "T03": "label_policy", "T04": "low_confidence", "T06": "no_confidence",
            "T08": "sensitive", "T09": "low_confidence", "T10": "low_confidence",
        })

    def test_pii_review_reasons(self):
        self.assertEqual(self._reasons("pii"), {
            "P02": "label_policy", "P03": "low_confidence", "P05": "low_confidence",
            "P06": "sensitive", "P08": "low_confidence",
        })

    def test_caption_review_reasons(self):
        self.assertEqual(self._reasons("caption"), {
            "C02": "low_confidence", "C03": "low_confidence", "C05": "low_confidence",
            "C06": "low_confidence", "C07": "sensitive", "C08": "low_confidence", "C09": "low_confidence",
        })


if __name__ == "__main__":
    unittest.main()
