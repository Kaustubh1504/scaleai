import unittest

from voxsplit.reports import build_report


class TestValidationSplit(unittest.TestCase):
    """The validation split is what the eval team pulls each week."""

    @classmethod
    def setUpClass(cls):
        cls.val = build_report()["splits"]["val"]

    def test_val_clips(self):
        self.assertEqual(self.val["clips"], ["C007", "C008", "C009", "C024", "C025", "C029", "C030"])

    def test_val_minutes(self):
        self.assertEqual(self.val["minutes"], 1.66)

    def test_val_accent_mix(self):
        self.assertEqual(self.val["accents"], {"in": 2, "uk": 2, "us": 3})


if __name__ == "__main__":
    unittest.main()
