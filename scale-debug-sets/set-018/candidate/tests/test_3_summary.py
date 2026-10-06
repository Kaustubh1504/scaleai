import unittest

from teleop.reports import build_report


class TestSummary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.summary = build_report()["summary"]

    def test_task_counts(self):
        self.assertEqual({t: (s["episodes"], s["valid"]) for t, s in self.summary["by_task"].items()},
                         {"fold_towel": (4, 2), "pick_place": (5, 3), "stack_blocks": (3, 2)})

    def test_success_rates(self):
        self.assertEqual({t: s["success_rate"] for t, s in self.summary["by_task"].items()},
                         {"fold_towel": 0.5, "pick_place": 0.333, "stack_blocks": 0.5})

    def test_6_valid_minutes(self):
        self.assertEqual(self.summary["valid_minutes"], 0.37)


if __name__ == "__main__":
    unittest.main()
