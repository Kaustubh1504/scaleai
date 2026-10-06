import unittest

from spanmerge.report import build_report


def flat(entities):
    return {doc: [(e["text"], e["label"], e["start"], e["end"], e["votes"]) for e in ents]
            for doc, ents in entities.items()}


class TestEntities(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_docs_with_entities(self):
        self.assertEqual(sorted(self.report["entities"]), ["d01", "d02", "d04", "d05", "d07", "d08", "d10"])

    def test_entities(self):
        self.maxDiff = None
        self.assertEqual(flat(self.report["entities"]), {
            "d01": [("Maria Lopez", "PER", 0, 11, 2), ("Acme Corp", "ORG", 19, 28, 2)],
            "d02": [("Red Cross", "ORG", 4, 13, 3), ("Nairobi", "LOC", 33, 40, 2)],
            "d04": [("Tim Cook", "PER", 0, 8, 3), ("Cupertino", "LOC", 32, 41, 2)],
            "d05": [("Lagos", "LOC", 0, 5, 3), ("African Union", "ORG", 45, 58, 2)],
            "d07": [("Siemens", "ORG", 0, 7, 2), ("Berlin", "LOC", 40, 46, 2)],
            "d08": [("Ana Silva", "PER", 0, 9, 3)],
            "d10": [("Ericsson", "ORG", 10, 18, 2)],
        })

    def test_label_counts(self):
        self.assertEqual(self.report["label_counts"], {"LOC": 4, "ORG": 5, "PER": 3})


if __name__ == "__main__":
    unittest.main()
