import unittest

from triage.reports import build_report


class TestRouting(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.decisions = build_report()["decisions"]

    def test_one_decision_per_prediction(self):
        ids = [d["pred_id"] for d in self.decisions]
        self.assertEqual(ids, [f"P{n:03d}" for n in range(1, 25)])

    def test_routes(self):
        auto = [d["pred_id"] for d in self.decisions if d["route"] == "auto"]
        self.assertEqual(auto, ["P001", "P002", "P003", "P004", "P007", "P008", "P009",
                                "P011", "P017", "P022", "P023"])

    def test_reasons(self):
        self.maxDiff = None
        reasons = {d["pred_id"]: d["reason"] for d in self.decisions if d["route"] == "human"}
        self.assertEqual(reasons, {
            "P005": "flagged", "P006": "no_score", "P010": "low_confidence",
            "P012": "flagged", "P013": "low_confidence", "P014": "no_score",
            "P015": "low_confidence", "P016": "low_confidence", "P018": "low_confidence",
            "P019": "flagged", "P020": "low_confidence", "P021": "low_confidence",
            "P024": "low_confidence",
        })


if __name__ == "__main__":
    unittest.main()
