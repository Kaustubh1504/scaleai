import unittest

from teleop.reports import build_report


def column(episodes, key):
    return {eid: e[key] for eid, e in episodes.items()}


class TestMetrics(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.episodes = build_report()["episodes"]

    def test_episode_ids(self):
        self.assertEqual(sorted(self.episodes), [f"EP{n:02d}" for n in range(1, 13)])

    def test_max_gaps(self):
        self.assertEqual(column(self.episodes, "max_gap_ms"), {
            "EP01": 100, "EP02": 100, "EP03": 140, "EP04": 100, "EP05": 100, "EP06": 150,
            "EP07": 100, "EP08": 260, "EP09": 100, "EP10": 100, "EP11": 100, "EP12": 100,
        })

    def test_1_frame_counts(self):
        self.assertEqual(column(self.episodes, "frames"), {
            "EP01": 30, "EP02": 41, "EP03": 25, "EP04": 18, "EP05": 15, "EP06": 35,
            "EP07": 31, "EP08": 30, "EP09": 40, "EP10": 51, "EP11": 21, "EP12": 28,
        })

    def test_2_durations(self):
        self.assertEqual(column(self.episodes, "duration_s"), {
            "EP01": 2.9, "EP02": 4.0, "EP03": 2.44, "EP04": 1.7, "EP05": 1.4, "EP06": 3.45,
            "EP07": 3.0, "EP08": 3.06, "EP09": 3.9, "EP10": 5.0, "EP11": 2.0, "EP12": 2.67,
        })

    def test_3_sync_rates(self):
        self.assertEqual(column(self.episodes, "sync_rate"), {
            "EP01": 1.0, "EP02": 1.0, "EP03": 1.0, "EP04": 1.0, "EP05": 1.0, "EP06": 0.771,
            "EP07": 1.0, "EP08": 1.0, "EP09": 0.5, "EP10": 1.0, "EP11": 1.0, "EP12": 1.0,
        })


if __name__ == "__main__":
    unittest.main()
