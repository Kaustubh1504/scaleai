import json
import unittest

from rosterflow.reports import build_report


class TestExport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()
        cls.exported = json.loads(cls.report["export"])

    def test_skill_counts(self):
        self.assertEqual(self.report["skill_counts"], {
            "excel": 1, "go": 2, "labeling": 1, "ml": 3, "nlp": 1, "python": 8,
            "qa": 2, "rust": 1, "spark": 2, "sql": 4,
        })

    def test_countries(self):
        self.assertEqual(self.report["countries"], {
            "AU": 1, "CZ": 1, "DE": 1, "ES": 1, "HK": 1, "IL": 1, "IN": 3, "KR": 2,
            "MX": 1, "NZ": 1, "SE": 1, "US": 1,
        })

    def test_export_order_and_fields(self):
        self.assertEqual([r["email"] for r in self.exported], sorted(self.report["roster"]))
        self.assertEqual(set(self.exported[0]), {"email", "name", "country", "hours", "skills", "sources", "updated_at"})

    def test_export_timestamps(self):
        self.maxDiff = None
        self.assertEqual({r["email"]: r["updated_at"] for r in self.exported}, {
            "ana@x.io": "2026-03-01T09:30:00", "cara@x.io": "2026-03-05T10:00:00",
            "dev@x.io": "2026-03-02T14:00:00", "eli@x.io": "2026-03-01T00:00:00",
            "fay@x.io": "2026-02-14T00:00:00", "gus@x.io": "2026-02-15T08:00:00",
            "kim@x.io": "2026-01-20T10:00:00", "mia@x.io": "2026-03-04T16:00:00",
            "noa@x.io": "2026-03-03T12:00:00", "raj@x.io": "2026-02-26T09:00:00",
            "tia@x.io": "2026-02-22T00:00:00", "uma@x.io": "2026-03-06T09:00:00",
            "wes@x.io": "2026-02-19T13:00:00", "xan@x.io": "2026-02-21T00:00:00",
            "zoe@x.io": "2026-03-02T07:30:00",
        })


if __name__ == "__main__":
    unittest.main()
