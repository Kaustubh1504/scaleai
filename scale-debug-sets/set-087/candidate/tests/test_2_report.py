import unittest

from chatpack.builder import build_dataset


class TestReport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.summary = build_dataset()["summary"]

    def test_examples_per_source(self):
        self.assertEqual(self.summary["examples_per_source"], {
            "code-review": 1, "dolly": 1, "internal-qa": 1, "math-tutor": 1,
            "oasst": 1, "sharegpt": 3, "vendor-a": 2, "vendor-b": 1,
        })

    def test_rejected_by_reason(self):
        self.assertEqual(self.summary["rejected_by_reason"], {"no_pair": 1, "too_long": 1, "unknown_source": 1})

    def test_3_tag_counts(self):
        self.assertEqual(self.summary["tag_counts"], {
            "billing": 1, "chitchat": 1, "code": 1, "cooking": 1, "general": 1, "greeting": 1,
            "math": 1, "news": 1, "qa": 1, "review": 1, "summarize": 1, "support": 2, "travel": 1,
        })


if __name__ == "__main__":
    unittest.main()
