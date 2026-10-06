import unittest

from sftfmt.reports import build_report


class TestReport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.summary = build_report()["summary"]

    def test_rejected(self):
        self.assertEqual(self.summary["rejected"], {
            "c04": "bad_turn_order", "c05": "no_assistant", "c08": "bad_turn_order", "c10": "no_assistant",
            "c12": "too_long", "c14": "bad_turn_order", "c16": "bad_turn_order",
        })

    def test_counts(self):
        self.assertEqual((self.summary["examples"], self.summary["mean_tokens"]), (9, 20.4))

    def test_assistant_turns(self):
        self.assertEqual(self.summary["assistant_turns"], 13)


if __name__ == "__main__":
    unittest.main()
