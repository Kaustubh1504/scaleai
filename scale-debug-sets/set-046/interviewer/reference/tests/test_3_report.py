import json
import unittest

from routedesk.reports import build_report, export_json


class TestReport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()
        cls.calibration = cls.report["calibration"]

    def test_agreement_rates(self):
        self.assertEqual(self.calibration["agreement"],
                         {"ads": 0.5, "hate": 1.0, "spam": 0.75, "toxic": 0.75})

    def test_5_reviewer_mix(self):
        self.assertEqual(self.calibration["reviewer_mix"], {
            "r-01": {"ham": 1, "spam": 2},
            "r-03": {"ok": 1, "toxic": 1},
            "r-04": {"ads": 1},
            "r-05": {"hate": 1, "ok": 1},
            "r-06": {"spam": 1, "toxic": 1},
            "r-09": {"toxic": 1},
        })

    def test_6_exported_timestamps(self):
        exported = json.loads(export_json(self.report))
        self.assertEqual(exported["calibration"]["last_review_at"], "2026-03-01T16:45:00")
        self.assertEqual(exported["sla"]["P-02"], "2026-03-02T11:05:00")
        self.assertEqual(exported["sla"]["P-21"], "2026-03-02T12:10:00")


if __name__ == "__main__":
    unittest.main()
