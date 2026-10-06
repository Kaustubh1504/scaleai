import unittest

from tonevote.reports import build_report


class TestReport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_overall_labels(self):
        self.assertEqual(self.report["labels"]["overall"], {"negative": 3, "neutral": 2, "positive": 5})

    def test_labels_by_project(self):
        self.assertEqual(self.report["labels"]["by_project"], {
            "chat": {"negative": 1, "positive": 3},
            "email": {"negative": 1, "neutral": 1, "positive": 1},
            "reviews": {"negative": 1, "neutral": 1, "positive": 1},
        })

    def test_team_summary(self):
        self.assertEqual(self.report["teams"], {
            "east": {"members": ["a07", "a08", "a10"], "votes": 13},
            "north": {"members": ["a01", "a02", "a03"], "votes": 23},
            "south": {"members": ["a04", "a05", "a06"], "votes": 20},
            "west": {"members": ["a12", "a13"], "votes": 0},
        })


if __name__ == "__main__":
    unittest.main()
