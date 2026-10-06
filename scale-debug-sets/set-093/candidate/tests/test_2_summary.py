import unittest

from quotecache.reports import build_report


class TestSummary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.summary = build_report()["summary"]

    def test_outcome_counts(self):
        counts = {k: self.summary[k] for k in ("requests", "hits", "misses", "errors", "hit_rate")}
        self.assertEqual(counts, {"requests": 26, "hits": 8, "misses": 16, "errors": 2, "hit_rate": 0.333})

    def test_origin_calls(self):
        self.assertEqual(self.summary["origin_calls"], {
            "SKU-1": 2, "SKU-2": 3, "SKU-3": 5, "SKU-4": 3, "SKU-5": 2, "SKU-6": 2, "SKU-9": 1,
        })

    def test_traffic_span(self):
        self.assertEqual((self.summary["span_hours"], self.summary["requests_per_hour"]), (25.5, 1.02))


if __name__ == "__main__":
    unittest.main()
