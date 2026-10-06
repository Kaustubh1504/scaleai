import unittest

from tests._harness import run_job


class TestReport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server, cls.sleeps, cls.report = run_job()

    @classmethod
    def tearDownClass(cls):
        cls.server.stop()

    def test_counts(self):
        self.assertEqual(self.report["counts"], {"ok": 5, "failed": 2, "rejected": 1})

    def test_index_coverage(self):
        self.assertEqual(self.report["index"], {
            "faq": {"stored": 9, "missing": []},
            "policies": {"stored": 3, "missing": []},
            "changelog": {"stored": 1, "missing": []},
            "pricing": {"stored": 0, "missing": []},
        })

    def test_requeue(self):
        self.assertEqual(self.report["requeue"], [
            "chg-201", "chg-202", "chg-203", "pol-101", "pol-103", "pol-104", "prc-301", "prc-302", "prc-303",
        ])


if __name__ == "__main__":
    unittest.main()
