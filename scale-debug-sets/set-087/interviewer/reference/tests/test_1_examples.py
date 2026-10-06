import unittest

from chatpack.builder import build_dataset


class TestExamples(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = build_dataset()
        cls.examples = cls.data["examples"]

    def test_kept_and_rejected_ids(self):
        self.assertEqual(sorted(self.examples),
                         ["c01", "c02", "c03", "c04", "c05", "c06", "c07", "c08", "c09", "c14", "c16"])
        self.assertEqual(self.data["rejected"], {"c10": "too_long", "c12": "unknown_source", "c13": "no_pair"})

    def test_role_cleanup(self):
        self.assertEqual(self.examples["c05"]["text"],
                         "<|user|>\nHow do I reset my password?\nIt says the link expired.\n"
                         "<|assistant|>\nRequest a new link from the login page.\n<|end|>")
        self.assertEqual(self.examples["c07"]["roles"], ["user", "assistant"])
        self.assertEqual(self.examples["c07"]["tokens"], 22)
        self.assertEqual(self.examples["c08"]["tokens"], 17)
        self.assertEqual(self.examples["c16"]["roles"], ["user", "assistant", "user", "assistant"])
        self.assertEqual(self.examples["c16"]["tokens"], 36)

    def test_oldest_pair_dropped_when_over_budget(self):
        self.assertEqual(self.examples["c04"]["dropped_pairs"], 1)
        self.assertEqual(self.examples["c04"]["tokens"], 27)
        self.assertTrue(self.examples["c04"]["text"].startswith("<|user|>\nAnd 3 times 3?\n"))

    def test_1_late_system_turn(self):
        self.assertEqual(self.examples["c06"], {
            "source": "sharegpt",
            "roles": ["system", "user", "assistant", "user", "assistant"],
            "tokens": 48,
            "dropped_pairs": 0,
            "text": "<|system|>\nYou are a friendly travel agent.\n"
                    "<|user|>\nFind me a hotel in Rome.\n"
                    "<|assistant|>\nHere are three options near the Colosseum.\n"
                    "<|user|>\nSomething cheaper please.\n"
                    "<|assistant|>\nTry the hostel on Via Cavour.\n<|end|>",
        })

    def test_2_vendor_b_example(self):
        ex = self.examples["c09"]
        self.assertEqual((ex["tokens"], ex["dropped_pairs"]), (64, 0))
        self.assertEqual(ex["roles"], ["user", "assistant", "user", "assistant"])


if __name__ == "__main__":
    unittest.main()
