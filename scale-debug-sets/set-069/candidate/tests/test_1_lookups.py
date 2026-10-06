import unittest

from guidecache.reports import build_report


class TestLookups(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lookups = build_report()["lookups"]

    def _project(self, project, fields=("outcome", "version")):
        return {rid: tuple(row[f] for f in fields) for rid, row in self.lookups.items() if row["project"] == project}

    def test_ner_lookups(self):
        self.assertEqual(self._project("ner"), {
            "N1": ("miss", 1), "N2": ("hit", 1), "N3": ("miss", 2), "N4": ("hit", 2), "N5": ("miss", 2),
        })

    def test_bbox_lookups(self):
        self.assertEqual(self._project("bbox", ("outcome", "version", "locale")), {
            "B1": ("miss", 1, "en"), "B2": ("miss", 1, "fr"), "B3": ("hit", 1, "en"),
            "B4": ("hit", 1, "fr"), "B5": ("miss", 1, "en"),
        })

    def test_sentiment_lookups(self):
        self.assertEqual(self._project("sentiment"), {
            "S1": ("miss", 3), "S2": ("hit", 3), "S3": ("hit", 3), "S4": ("hit", 3),
            "S5": ("hit", 3), "S6": ("miss", 3),
        })

    def test_not_found(self):
        missing = sorted(rid for rid, row in self.lookups.items() if row["outcome"] == "not_found")
        self.assertEqual(missing, ["X1", "X2"])


if __name__ == "__main__":
    unittest.main()
