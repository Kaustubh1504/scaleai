import unittest

from spanalign.reports import build_report


class TestSpanNormalization(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_exported_spans(self):
        self.maxDiff = None
        self.assertEqual(self.report["export"], {
            "D07": [[0, 12, "PERSON", "ann-a", "Liam O'Brien"],
                    [25, 38, "ORG", "ann-a", "Redwood Media"],
                    [52, 58, "LOC", "ann-a", "Dublin"]],
            "D08": [[0, 18, "ORG", "ann-b", "Global Freight Inc"]],
            "D09": [[0, 11, "PERSON", "ann-b", "Sofia Rossi"],
                    [53, 58, "LOC", "ann-b", "Milan"]],
            "D10": [[0, 13, "PERSON", "ann-d", "Hannah Becker"],
                    [38, 49, "ORG", "ann-d", "Alpine Data"]],
            "D12": [[23, 40, "ORG", "ann-d", "Silverline Energy"]],
        })

    def test_rejection_reasons(self):
        self.assertEqual(self.report["rejected"], {
            "duplicate": 2, "empty": 1, "missing_offset": 1,
            "out_of_range": 2, "unknown_doc": 1, "unknown_label": 2,
        })

    def test_accepted_per_annotator(self):
        self.assertEqual(self.report["accepted"], {"ann-a": 11, "ann-b": 11, "ann-c": 6, "ann-d": 3})


if __name__ == "__main__":
    unittest.main()
