import unittest

from turnsmith.export import build_dataset


class TestSummary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = build_dataset()
        cls.summary = cls.data["summary"]

    def test_rejections(self):
        self.assertEqual(
            self.data["rejected"],
            {"c04": "excluded", "c06": "no_pair", "c07": "too_long", "c11": "excluded"},
        )
        self.assertEqual(self.summary["rejected_by_reason"], {"excluded": 2, "no_pair": 1, "too_long": 1})

    def test_example_count(self):
        self.assertEqual(self.summary["examples"], 7)

    def test_tag_counts(self):
        self.assertEqual(
            self.summary["tag_counts"],
            {"billing": 2, "coding": 1, "general": 2, "returns": 2, "shipping": 2},
        )

    def test_total_tokens(self):
        self.assertEqual(self.summary["total_tokens"], 295)


if __name__ == "__main__":
    unittest.main()
