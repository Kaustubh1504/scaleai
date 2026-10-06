import unittest

from triage.reports import build_report


class TestSummary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.summary = build_report()["summary"]

    def test_by_task_type(self):
        self.assertEqual(self.summary["by_task_type"], {
            "intent": {"auto": 2, "human": 5, "human_rate": 0.714},
            "sentiment": {"auto": 3, "human": 2, "human_rate": 0.4},
            "spam": {"auto": 3, "human": 2, "human_rate": 0.4},
            "toxicity": {"auto": 3, "human": 4, "human_rate": 0.571},
        })

    def test_busiest_reviewer(self):
        self.assertEqual(self.summary["busiest_reviewer"], "R02")

    def test_backlog_size(self):
        self.assertEqual(self.summary["backlog_size"], 4)


if __name__ == "__main__":
    unittest.main()
