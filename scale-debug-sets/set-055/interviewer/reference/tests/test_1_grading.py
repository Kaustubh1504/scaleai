import unittest

from evalscore.reports import build_report


class TestGrading(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_models(self):
        self.assertEqual(sorted(self.report["correct"]), ["alpha", "bravo", "charlie", "delta"])

    def test_correct_items(self):
        self.assertEqual(self.report["correct"], {
            "alpha": ["I01", "I02", "I03", "I04", "I05", "I06", "I07", "I08", "I09"],
            "bravo": ["I01", "I03", "I04", "I09"],
            "charlie": ["I01", "I02", "I05", "I07", "I08", "I11", "I12"],
            "delta": ["I01", "I02"],
        })

    def test_unscored_items(self):
        self.assertEqual(self.report["unscored"], {
            "alpha": {"errored": [], "unparsed": []},
            "bravo": {"errored": [], "unparsed": []},
            "charlie": {"errored": [], "unparsed": []},
            "delta": {"errored": ["I05", "I09"], "unparsed": ["I07"]},
        })


if __name__ == "__main__":
    unittest.main()
