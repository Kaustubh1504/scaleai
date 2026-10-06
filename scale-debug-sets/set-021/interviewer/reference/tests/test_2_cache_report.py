import json
import unittest

from labelcache.reports import report_json


class TestCacheReport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = json.loads(report_json())

    def test_model_versions(self):
        versions = {m: row["version"] for m, row in self.report["models"].items()}
        self.assertEqual(versions, {"ner-v3": 2, "ocr-v1": 2, "seg-v2": 2})

    def test_last_refresh(self):
        refreshed = {m: row["last_refresh"] for m, row in self.report["models"].items()}
        self.assertEqual(refreshed, {
            "ner-v3": "2026-03-02T09:15:30",
            "ocr-v1": "2026-03-02T09:12:00",
            "seg-v2": "2026-03-02T09:14:30",
        })

    def test_snapshot(self):
        self.maxDiff = None
        self.assertEqual(self.report["snapshot"], [
            {"task_id": "T03", "model": "ner-v3", "locale": "de-de",
             "value": "ner-v3@2/T03/de-de", "expires_at": "2026-03-02T09:20:30"},
            {"task_id": "T04", "model": "ner-v3", "locale": "en-us",
             "value": "ner-v3@2/T04/en-us", "expires_at": "2026-03-02T09:18:30"},
            {"task_id": "T01", "model": "ocr-v1", "locale": "fr-fr",
             "value": "ocr-v1@2/T01/fr-fr", "expires_at": "2026-03-02T09:17:30"},
            {"task_id": "T06", "model": "ocr-v1", "locale": "ja-jp",
             "value": "ocr-v1@2/T06/ja-jp", "expires_at": "2026-03-02T09:22:00"},
            {"task_id": "T07", "model": "ocr-v1", "locale": "en-us",
             "value": "ocr-v1@2/T07/en-us", "expires_at": "2026-03-02T09:19:30"},
            {"task_id": "T02", "model": "seg-v2", "locale": "en-us",
             "value": "seg-v2@2/T02/en-us", "expires_at": "2026-03-02T09:16:30"},
        ])


if __name__ == "__main__":
    unittest.main()
