import unittest

from robolog.report import build_report

VALID = ["EP-01", "EP-02", "EP-03", "EP-07", "EP-08", "EP-09", "EP-10", "EP-11", "EP-12", "EP-13", "EP-15", "EP-16"]


class TestValidity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.episodes = build_report()["episodes"]

    def test_validity_and_reasons(self):
        self.assertEqual(sorted(e for e, s in self.episodes.items() if s["valid"]), VALID)
        self.assertEqual({e: s["reason"] for e, s in self.episodes.items() if not s["valid"]},
                         {"EP-04": "missing_stream", "EP-05": "frame_gap", "EP-06": "unsynced", "EP-14": "too_short"})

    def test_frame_stats(self):
        got = {e: (s["frames"], s["duration_s"], s["max_gap_ms"]) for e, s in self.episodes.items()}
        self.assertEqual(got["EP-05"], (50, 2.12, 200))
        self.assertEqual(got["EP-07"], (45, 1.45, 33))
        self.assertEqual(got["EP-10"], (48, 1.99, 150))
        self.assertEqual(got["EP-14"], (12, 0.44, 40))

    def test_sync_ratios(self):
        self.assertEqual({e: s["sync_ratio"] for e, s in self.episodes.items() if s["sync_ratio"] != 1.0},
                         {"EP-04": None, "EP-06": 0.66, "EP-11": 0.9})

    def test_frame_rates(self):
        self.assertEqual({e: s["fps"] for e, s in self.episodes.items() if s["fps"] != 25.0},
                         {"EP-05": 23.11, "EP-07": 30.3, "EP-09": 20.0, "EP-10": 23.62,
                          "EP-13": 27.78, "EP-15": 33.33})


if __name__ == "__main__":
    unittest.main()
