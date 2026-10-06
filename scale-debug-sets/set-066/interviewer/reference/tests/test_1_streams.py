import unittest

from episodekit.reports import build_report


class TestStreams(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_episode_ids(self):
        self.assertEqual(self.report["episode_ids"], [f"EP-{n:02d}" for n in range(1, 15)])

    def test_camera_stats(self):
        self.maxDiff = None
        self.assertEqual(self.report["camera"], {
            "EP-01": {"frames": 8, "duration_ms": 700, "max_gap_ms": 100},
            "EP-02": {"frames": 8, "duration_ms": 700, "max_gap_ms": 100},
            "EP-03": {"frames": 10, "duration_ms": 450, "max_gap_ms": 50},
            "EP-04": {"frames": 7, "duration_ms": 600, "max_gap_ms": 100},
            "EP-05": {"frames": 6, "duration_ms": 500, "max_gap_ms": 100},
            "EP-06": {"frames": 5, "duration_ms": 400, "max_gap_ms": 100},
            "EP-07": {"frames": 8, "duration_ms": 700, "max_gap_ms": 100},
            "EP-08": {"frames": 7, "duration_ms": 800, "max_gap_ms": 300},
            "EP-09": {"frames": 7, "duration_ms": 350, "max_gap_ms": 100},
            "EP-10": {"frames": 7, "duration_ms": 400, "max_gap_ms": 67},
            "EP-11": {"frames": 8, "duration_ms": 700, "max_gap_ms": 100},
            "EP-13": {"frames": 8, "duration_ms": 800, "max_gap_ms": 200},
            "EP-14": {"frames": 7, "duration_ms": 240, "max_gap_ms": 40},
        })

    def test_joint_samples(self):
        self.assertEqual(self.report["joint_samples"], {
            "EP-01": 9, "EP-02": 8, "EP-03": 10, "EP-04": 7, "EP-05": 6, "EP-06": 5,
            "EP-07": 8, "EP-08": 7, "EP-09": 7, "EP-11": 8, "EP-13": 8, "EP-14": 7,
        })


if __name__ == "__main__":
    unittest.main()
