import unittest

from fraudlens.reports import build_report


class TestScoring(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.decisions = build_report()["decisions"]

    def card(self, card_id):
        return {tid: (d["flags"], d["action"]) for tid, d in self.decisions.items() if d["card"] == card_id}

    def test_clean_card(self):
        self.assertEqual(self.card("c01"), {"T001": ([], "allow")})

    def test_velocity_window(self):
        self.assertEqual(self.card("c02"), {
            "T002": ([], "allow"),
            "T003": ([], "allow"),
            "T006": (["velocity"], "review"),
            "T028": ([], "allow"),
        })

    def test_burst_abroad(self):
        self.assertEqual(self.card("c03"), {
            "T004": (["foreign"], "allow"),
            "T005": (["foreign"], "allow"),
            "T007": (["velocity", "foreign"], "block"),
        })

    def test_daily_limit(self):
        self.assertEqual(self.card("c04"), {
            "T008": ([], "allow"),
            "T010": ([], "allow"),
            "T012": (["over_limit"], "review"),
            "T026": ([], "allow"),
        })

    def test_unknown_currency(self):
        self.assertEqual(self.card("c05"), {
            "T009": ([], "allow"),
            "T011": (["unknown_currency:ZAR"], "review"),
            "T023": (["foreign"], "allow"),
        })

    def test_converted_amounts(self):
        usd = {tid: d["usd"] for tid, d in self.decisions.items() if d["card"] in ("c07", "c08", "c10")}
        self.assertEqual(usd, {"T017": 80.4, "T020": 56.95, "T019": 33.3, "T025": 334.8, "T030": 129.6})


if __name__ == "__main__":
    unittest.main()
