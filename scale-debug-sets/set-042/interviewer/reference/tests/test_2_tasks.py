import unittest

from robolog.report import build_report


class TestTaskMetrics(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tasks = build_report()["tasks"]

    def test_episode_counts(self):
        self.assertEqual({t: m["episodes"] for t, m in self.tasks.items()},
                         {"pick": 5, "place": 3, "pour": 2, "wipe": 2})

    def test_success_rates(self):
        self.assertEqual({t: m["success_rate"] for t, m in self.tasks.items()},
                         {"pick": 0.6, "place": 1.0, "pour": 0.0, "wipe": 0.5})

    def test_recorded_seconds(self):
        self.assertEqual({t: m["recorded_s"] for t, m in self.tasks.items()},
                         {"pick": 11.07, "place": 6.12, "pour": 3.5, "wipe": 3.94})


if __name__ == "__main__":
    unittest.main()
