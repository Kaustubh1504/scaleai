import unittest

from hitlroute.reports import build_report


class TestAssignment(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        report = build_report()
        cls.assignments = report["assignments"]
        cls.backlog = report["backlog"]

    def pool(self, *reviewers, lang):
        return {r: self.assignments[r] for r in reviewers}, self.backlog.get(lang)

    def test_every_reviewer_listed(self):
        self.assertEqual(sorted(self.assignments), [f"rv-{n:02d}" for n in range(1, 12)])

    def test_english_pool(self):
        self.assertEqual(self.pool("rv-01", "rv-02", "rv-03", "rv-04", lang="en"), (
            {"rv-01": ["I03", "I11"], "rv-02": ["I02", "I14"], "rv-03": ["L03", "I19"], "rv-04": []},
            [],
        ))

    def test_spanish_pool(self):
        self.assertEqual(self.pool("rv-05", "rv-06", "rv-07", lang="es"), (
            {"rv-05": ["I05", "I12"], "rv-06": [], "rv-07": ["I04", "I18"]},
            ["I20"],
        ))

    def test_german_pool(self):
        self.assertEqual(self.pool("rv-08", "rv-09", "rv-10", lang="de"), (
            {"rv-08": ["I16", "I10"], "rv-09": ["I07"], "rv-10": []},
            ["I13", "I17"],
        ))

    def test_pools_without_work(self):
        self.assertEqual((self.assignments["rv-11"], sorted(self.backlog)), ([], ["de", "en", "es"]))


if __name__ == "__main__":
    unittest.main()
