import unittest

from holdout.reports import build_report


class TestAssignment(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_intent_groups(self):
        self.assertEqual(self.report["intent"]["groups"], {
            "in-d01": "train", "in-d02": "test", "in-d03": "train", "in-d04": "train",
            "in-d05": "val", "in-d06": "train", "in-d07": "val",
        })

    def test_toxicity_groups(self):
        self.assertEqual(self.report["toxicity"]["groups"], {
            "tox-d01": "train", "tox-d02": "train", "tox-d03": "val", "tox-d05": "test",
            "tox-d06": "test", "tox-d07": "val", "tox-d09": "test",
        })

    def test_intent_pin_honoured(self):
        self.assertEqual(self.report["intent"]["groups"]["in-d02"], "test")

    def test_sizes_add_up(self):
        for name, ds in self.report.items():
            with self.subTest(dataset=name):
                self.assertEqual(sum(ds["sizes"].values()), ds["kept"])
                self.assertEqual(set(ds["groups"].values()) <= {"train", "val", "test"}, True)


if __name__ == "__main__":
    unittest.main()
