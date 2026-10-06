import unittest

from routedesk.reports import build_report

HUMAN = {"P-02", "P-04", "P-10", "P-11", "P-13", "P-14", "P-15", "P-16", "P-17", "P-18",
         "P-19", "P-21", "P-22", "P-26"}
V2_THRESHOLDS = {"P-03": 0.95, "P-04": 0.95, "P-06": 0.92, "P-08": 0.88, "P-11": 0.95,
                 "P-16": 0.75, "P-18": 0.92, "P-24": 0.95}


class TestRouting(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.routing = build_report()["routing"]

    def test_one_row_per_item(self):
        expected = [f"P-{n:02d}" for n in range(1, 23)] + ["P-24", "P-26"]
        self.assertEqual(sorted(self.routing), expected)

    def test_1_thresholds_for_v2_items(self):
        got = {iid: row["threshold"] for iid, row in self.routing.items() if iid in V2_THRESHOLDS}
        self.assertEqual(got, V2_THRESHOLDS)

    def test_2_decisions(self):
        decisions = {iid: row["decision"] for iid, row in self.routing.items()}
        expected = {iid: ("human" if iid in HUMAN else "auto") for iid in self.routing}
        self.assertEqual(decisions, expected)

    def test_missing_confidence_reason(self):
        self.assertEqual(self.routing["P-11"]["reason"], "missing_confidence")


if __name__ == "__main__":
    unittest.main()
