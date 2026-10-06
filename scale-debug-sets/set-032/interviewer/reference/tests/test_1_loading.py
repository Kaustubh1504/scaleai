import unittest

from vendorfeed.reports import build_report


class TestLoading(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_rows_read(self):
        self.assertEqual(self.report["rows_read"], {"acme": 14, "brightlabel": 13, "cortex": 12})

    def test_rejections(self):
        self.maxDiff = None
        self.assertEqual(self.report["rejected"], {
            "acme:4": ["bad_email"],
            "acme:7": ["missing_task_id"],
            "acme:8": ["missing_duration"],
            "acme:11": ["bad_timestamp"],
            "acme:12": ["negative_duration"],
            "acme:14": ["bad_email", "bad_timestamp"],
            "brightlabel:9": ["bad_email"],
            "brightlabel:13": ["bad_timestamp"],
            "cortex:6": ["missing_duration"],
            "cortex:10": ["bad_timestamp"],
        })


if __name__ == "__main__":
    unittest.main()
