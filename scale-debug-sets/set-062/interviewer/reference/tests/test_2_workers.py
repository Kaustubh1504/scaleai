import unittest

from relaymesh.report import build_report

CENTRAL = ("cen-1", "cen-2", "cen-3", "cen-4")


class TestWorkerStats(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        workers = build_report()["workers"]
        cls.central = {wid: workers[wid] for wid in CENTRAL}
        cls.workers = workers

    def test_all_workers_reported(self):
        self.assertEqual(len(self.workers), 13)

    def test_central_served_and_busy(self):
        got = {w: (s["served"], s["busy_s"]) for w, s in self.central.items()}
        self.assertEqual(got, {"cen-1": (5, 11.5), "cen-2": (3, 5.2), "cen-3": (2, 3.3), "cen-4": (0, 0.0)})

    def test_3_central_utilisation(self):
        got = {w: s["utilisation_pct"] for w, s in self.central.items()}
        self.assertEqual(got, {"cen-1": 115.0, "cen-2": 52.0, "cen-3": 33.0, "cen-4": 0.0})

    def test_4_central_peak_inflight(self):
        got = {w: s["peak_inflight"] for w, s in self.central.items()}
        self.assertEqual(got, {"cen-1": 3, "cen-2": 2, "cen-3": 1, "cen-4": 0})


if __name__ == "__main__":
    unittest.main()
