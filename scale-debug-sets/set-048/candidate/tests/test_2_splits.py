import unittest

from splitkit.reports import build_report

GROUP_LABELS = {
    "g-01": "cat", "g-02": "cat", "g-03": "cat", "g-04": "dog", "g-05": "cat", "g-06": "dog",
    "g-07": "cat", "g-08": "dog", "g-09": "cat", "g-10": "bird", "g-11": "cat", "g-12": "bird",
    "g-13": "cat", "g-14": "bird", "g-15": "bird", "g-16": "dog",
}
GROUP_SPLIT = {
    "g-01": "test", "g-02": "test", "g-03": "val", "g-04": "test", "g-05": "val", "g-06": "val",
    "g-07": "train", "g-08": "train", "g-09": "train", "g-10": "test", "g-11": "train",
    "g-12": "val", "g-13": "train", "g-14": "train", "g-15": "train", "g-16": "train",
}


class TestSplits(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_group_labels(self):
        self.assertEqual(self.report["group_labels"], GROUP_LABELS)

    def test_every_group_assigned(self):
        self.assertEqual(sorted(self.report["group_split"]), sorted(GROUP_LABELS))

    def test_group_split(self):
        self.maxDiff = None
        self.assertEqual(self.report["group_split"], GROUP_SPLIT)


if __name__ == "__main__":
    unittest.main()
