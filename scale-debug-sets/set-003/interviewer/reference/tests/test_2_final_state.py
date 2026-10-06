import unittest

from leasequeue.reports import build_report


class TestFinalState(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_status(self):
        self.assertEqual(self.report["status"], {
            "A-101": "done", "A-102": "done", "A-103": "done", "A-104": "done",
            "A-105": "pending", "A-106": "done", "A-107": "pending", "A-108": "done",
            "A-109": "pending", "A-110": "dead",
        })

    def test_dead_letter(self):
        self.assertEqual(self.report["dead_letter"], ["A-110"])

    def test_attempts(self):
        self.assertEqual(self.report["attempts"], {
            "A-101": 1, "A-102": 1, "A-103": 1, "A-104": 1, "A-105": 0,
            "A-106": 1, "A-107": 0, "A-108": 2, "A-109": 1, "A-110": 2,
        })

    def test_rejected_completions(self):
        self.assertEqual(self.report["rejected"], [
            ["2026-04-01 08:41", "w3", "A-110"],
            ["2026-04-02 08:46", "w4", "A-110"],
            ["2026-04-02 09:20", "w3", "A-108"],
            ["2026-04-02 09:36", "w4", "A-999"],
        ])

    def test_completed_by(self):
        self.assertEqual(self.report["completed_by"], {"w1": 3, "w2": 2, "w5": 1})


if __name__ == "__main__":
    unittest.main()
