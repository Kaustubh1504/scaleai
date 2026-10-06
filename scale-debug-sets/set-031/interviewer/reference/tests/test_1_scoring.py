import unittest

from evalscore.reports import build_report


class TestScoring(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.models = build_report()["models"]

    def test_models_found(self):
        self.assertEqual(sorted(self.models), ["atlas-7b", "boreal-13b"])

    def test_correct_items(self):
        self.assertEqual(self.models["atlas-7b"]["correct"],
                         ["Q01", "Q02", "Q03", "Q07", "Q08", "Q09", "Q11", "Q12"])
        self.assertEqual(self.models["boreal-13b"]["correct"],
                         ["Q02", "Q04", "Q05", "Q07", "Q10", "Q11", "Q12"])

    def test_unparsed_and_failed(self):
        got = {m: (r["unparsed"], r["failed"]) for m, r in self.models.items()}
        self.assertEqual(got, {
            "atlas-7b": (["Q06"], ["Q05"]),
            "boreal-13b": (["Q08"], ["Q03", "Q09"]),
        })

    def test_accuracy(self):
        got = {m: r["accuracy"] for m, r in self.models.items()}
        self.assertEqual(got, {"atlas-7b": 0.621, "boreal-13b": 0.655})


if __name__ == "__main__":
    unittest.main()
