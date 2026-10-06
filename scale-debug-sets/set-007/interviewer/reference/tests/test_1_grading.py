import unittest

from evalscore.reports import build_report


class TestGrading(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.responses = build_report()["responses"]

    def test_all_responses_graded(self):
        self.assertEqual(len(self.responses), 36)
        self.assertEqual(self.responses["r01"]["model"], "atlas-7b")
        self.assertEqual(self.responses["r09"]["item"], "q09")

    def test_extracted_answers(self):
        got = {rid: self.responses[rid]["answer"] for rid in ("r02", "r03", "r04", "r06", "r12", "r23", "r35")}
        self.assertEqual(got, {"r02": "D", "r03": "C", "r04": "C", "r06": None,
                               "r12": "D", "r23": "C", "r35": "C"})

    def test_correct_per_model(self):
        counts = {}
        for row in self.responses.values():
            counts[row["model"]] = counts.get(row["model"], 0) + int(row["correct"])
        self.assertEqual(counts, {"atlas-7b": 8, "borealis-13b": 8, "cirrus-3b": 7})

    def test_flags(self):
        flagged = {rid: row["flags"] for rid, row in self.responses.items() if row["flags"]}
        self.assertEqual(flagged, {
            "r03": ["multiple_answers"], "r06": ["no_answer"], "r21": ["no_answer"],
            "r23": ["multiple_answers"], "r35": ["multiple_answers"], "r36": ["no_answer"],
        })


if __name__ == "__main__":
    unittest.main()
