import unittest

from lbsim.reports import build_report


class TestHealth(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_pool_loaded(self):
        self.assertEqual(sorted(self.report["workers"]), [f"W-{n:02d}" for n in range(1, 11)])

    def test_1_worker_states(self):
        self.assertEqual(self.report["workers"], {
            "W-01": "up", "W-02": "down", "W-03": "up", "W-04": "up", "W-05": "up",
            "W-06": "up", "W-07": "up", "W-08": "draining", "W-09": "up", "W-10": "up",
        })

    def test_2_availability(self):
        self.assertEqual(self.report["availability"], {
            "W-01": 1.0, "W-02": 0.0, "W-03": None, "W-04": 0.0, "W-05": None,
            "W-06": 1.0, "W-07": 1.0, "W-08": 0.0, "W-09": 1.0, "W-10": 0.0,
        })


if __name__ == "__main__":
    unittest.main()
