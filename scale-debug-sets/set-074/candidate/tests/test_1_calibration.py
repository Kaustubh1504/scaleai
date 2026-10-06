import unittest

from likert.reports import build_report

EXPECTED = {
    "a01": {"v1": 1.0, "v2": 0.0},
    "a02": {"v1": 0.0, "v2": 0.5},
    "a03": {"v1": -1.0, "v2": -1.0},
    "a04": {"v1": 0.0, "v2": 0.0},
    "a05": {"v1": 0.5, "v2": 0.0},
    "a06": {"v1": 0.0, "v2": 0.0},
    "a07": {"v1": 0.0, "v2": 1.0},
    "a08": {"v1": 0.0, "v2": -2.0},
}


class TestCalibration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bias = build_report()["bias"]

    def test_active_annotators_only(self):
        self.assertEqual(sorted(self.bias), sorted(EXPECTED))

    def test_bias_table(self):
        self.maxDiff = None
        self.assertEqual(self.bias, EXPECTED)


if __name__ == "__main__":
    unittest.main()
