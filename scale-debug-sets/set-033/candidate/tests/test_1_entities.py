import unittest

from spanmerge.reports import build_report

EXPECTED = {
    "D01": [(0, 13, "PER", "Angela Merkel", 3), (22, 27, "LOC", "Paris", 2)],
    "D02": [(0, 5, "ORG", "Apple", 2), (29, 35, "LOC", "Austin", 2)],
    "D03": [(0, 10, "PER", "Washington", 3), (32, 37, "LOC", "Ghent", 2)],
    "D04": [(4, 29, "ORG", "World Health Organization", 2), (37, 43, "LOC", "Geneva", 3)],
    "D05": [(21, 32, "PER", "Naomi Osaka", 3)],
    "D06": [(0, 6, "ORG", "Toyota", 2)],
    "D07": [(19, 28, "ORG", "Petrobras", 3)],
    "D08": [],
    "D09": [(22, 31, "PER", "Raj Patel", 2)],
    "D10": [(25, 30, "LOC", "Kyoto", 2)],
}


class TestEntities(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.entities = build_report()["entities"]

    def project(self, *fields):
        return {doc: [tuple(e[f] for f in fields) for e in ents] for doc, ents in self.entities.items()}

    def test_documents_listed(self):
        self.assertEqual(sorted(self.entities), sorted(EXPECTED))

    def test_entity_offsets(self):
        self.maxDiff = None
        want = {doc: [e[:3] for e in ents] for doc, ents in EXPECTED.items()}
        self.assertEqual(self.project("start", "end", "label"), want)

    def test_entity_text(self):
        self.maxDiff = None
        want = {doc: [e[3] for e in ents] for doc, ents in EXPECTED.items()}
        got = {doc: [t for (t,) in ents] for doc, ents in self.project("text").items()}
        self.assertEqual(got, want)

    def test_votes(self):
        self.maxDiff = None
        want = {doc: [e[4] for e in ents] for doc, ents in EXPECTED.items()}
        got = {doc: [v for (v,) in ents] for doc, ents in self.project("votes").items()}
        self.assertEqual(got, want)


if __name__ == "__main__":
    unittest.main()
