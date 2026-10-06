import unittest

from quorum.reports import build_report


class TestQualityReport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.quality = build_report()["queues"]["quality"]

    def test_status_counts(self):
        self.assertEqual(self.quality["status_counts"], {"accepted": 3, "escalated": 1, "pending": 1})

    def test_annotator_agreement(self):
        self.assertEqual(self.quality["agreement"], {
            "a01": 1.0, "a02": 1.0, "a03": 1.0, "a04": 1.0, "a07": 1.0, "a08": 0.0, "a11": 0.667,
        })

    def test_contested(self):
        self.assertEqual(self.quality["contested"], ["Q01", "Q02"])


if __name__ == "__main__":
    unittest.main()
