import unittest

from labelcache.reports import build_report


def lookups(report, model):
    return [(o["ts"][11:], o["task_id"], o["locale"], o["result"], o["value"])
            for o in report["outcomes"] if o["model"] == model]


class TestLookups(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_fetch_rows_replayed(self):
        self.assertEqual(len(self.report["outcomes"]), 25)

    def test_ocr_lookups(self):
        self.assertEqual(lookups(self.report, "ocr-v1"), [
            ("09:00:00", "T01", "en-us", "miss", "ocr-v1@1/T01/en-us"),
            ("09:01:00", "T01", "en-us", "hit", "ocr-v1@1/T01/en-us"),
            ("09:02:00", "T01", "fr-fr", "miss", "ocr-v1@1/T01/fr-fr"),
            ("09:04:00", "T01", "fr-fr", "hit", "ocr-v1@1/T01/fr-fr"),
            ("09:07:30", "T01", "fr-fr", "miss", "ocr-v1@2/T01/fr-fr"),
            ("09:09:30", "T07", "en-us", "miss", "ocr-v1@2/T07/en-us"),
            ("09:12:00", "T06", "ja-jp", "miss", "ocr-v1@2/T06/ja-jp"),
            ("09:14:00", "T07", "en-us", "hit", "ocr-v1@2/T07/en-us"),
            ("09:15:00", "T06", "ja-jp", "hit", "ocr-v1@2/T06/ja-jp"),
        ])

    def test_seg_lookups(self):
        self.assertEqual(lookups(self.report, "seg-v2"), [
            ("09:00:30", "T02", "en-us", "miss", "seg-v2@1/T02/en-us"),
            ("09:02:30", "T02", "en-us", "miss", "seg-v2@1/T02/en-us"),
            ("09:03:00", "T02", "en-us", "hit", "seg-v2@1/T02/en-us"),
            ("09:08:30", "T02", "en-us", "miss", "seg-v2@2/T02/en-us"),
            ("09:09:00", "T05", "fr-fr", "miss", "seg-v2@2/T05/fr-fr"),
            ("09:10:15", "T02", "en-us", "hit", "seg-v2@2/T02/en-us"),
            ("09:11:05", "T05", "fr-fr", "miss", "seg-v2@2/T05/fr-fr"),
            ("09:14:30", "T02", "en-us", "miss", "seg-v2@2/T02/en-us"),
        ])

    def test_ner_lookups(self):
        self.assertEqual(lookups(self.report, "ner-v3"), [
            ("09:01:30", "T03", "de-de", "miss", "ner-v3@1/T03/de-de"),
            ("09:03:30", "T03", "de-de", "hit", "ner-v3@1/T03/de-de"),
            ("09:05:00", "T04", "en-us", "miss", "ner-v3@1/T04/en-us"),
            ("09:07:00", "T03", "de-de", "miss", "ner-v3@1/T03/de-de"),
            ("09:09:59", "T04", "en-us", "hit", "ner-v3@1/T04/en-us"),
            ("09:12:30", "T03", "de-de", "miss", "ner-v3@1/T03/de-de"),
            ("09:13:30", "T04", "en-us", "miss", "ner-v3@2/T04/en-us"),
            ("09:15:30", "T03", "de-de", "miss", "ner-v3@2/T03/de-de"),
        ])


if __name__ == "__main__":
    unittest.main()
