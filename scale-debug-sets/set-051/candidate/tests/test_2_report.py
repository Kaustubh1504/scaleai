import unittest

from leasebook.reports import build_report


class TestReport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_workers(self):
        self.maxDiff = None
        self.assertEqual(self.report["workers"], {
            "alice": {"claims": 2, "acks": 0, "lost": 2},
            "bob": {"claims": 4, "acks": 1, "lost": 3},
            "cara": {"claims": 3, "acks": 1, "lost": 2},
            "dan": {"claims": 2, "acks": 1, "lost": 1},
            "erin": {"claims": 3, "acks": 2, "lost": 1},
            "frank": {"claims": 2, "acks": 1, "lost": 1},
            "gina": {"claims": 2, "acks": 0, "lost": 2},
        })

    def test_total_acks_match_done_tasks(self):
        done = sum(1 for s in self.report["status"].values() if s == "done")
        self.assertEqual(sum(w["acks"] for w in self.report["workers"].values()), done)

    def test_dead_letter(self):
        self.assertEqual(self.report["dead_letter"], ["T02", "T06"])

    def test_extensions(self):
        self.assertEqual(self.report["extensions"], {"T01": 2, "T05": 1, "T07": 1})


if __name__ == "__main__":
    unittest.main()
