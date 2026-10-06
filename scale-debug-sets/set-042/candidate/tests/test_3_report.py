import unittest

from robolog.report import build_report


class TestSummary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.summary = build_report()["summary"]

    def test_valid_count_and_rejections(self):
        self.assertEqual(self.summary["valid_episodes"], 12)
        self.assertEqual(self.summary["rejected"],
                         {"frame_gap": 1, "missing_stream": 1, "too_short": 1, "unsynced": 1})

    def test_tag_counts(self):
        self.assertEqual(self.summary["tag_counts"],
                         {"grasp": 3, "pick": 3, "place": 2, "pour": 1, "regrasp": 1, "slow": 1, "wipe": 2})
        self.assertEqual(self.summary["untagged"], ["EP-02", "EP-07", "EP-16"])

    def test_operator_counts(self):
        self.assertEqual(self.summary["operators"], {"alice": 4, "bob": 3, "carol": 1, "dave": 4})


if __name__ == "__main__":
    unittest.main()
