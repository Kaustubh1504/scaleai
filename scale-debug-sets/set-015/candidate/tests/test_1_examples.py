import unittest

from sftpack.reports import build_report

C05_TEXT = (
    "<|system|>\nYou are a friendly travel assistant.\n"
    "<|user|>\nHow many days do I need?\n"
    "<|assistant|>\nPlan at least ten days to see both cities without rushing.\n"
    "<|end|>\n"
)


class TestExamples(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_truncation_keeps_system_prompt(self):
        self.assertEqual((self.report["examples"]["c05"]["status"], self.report["examples"]["c05"]["turns"]),
                         ("truncated", 3))

    def test_1_outcomes(self):
        outcomes = {cid: (ex["status"], ex["tokens"]) for cid, ex in self.report["examples"].items()}
        self.assertEqual(outcomes, {
            "c01": ("ok", 28), "c02": ("ok", 23), "c03": ("ok", 19), "c04": ("ok", 17),
            "c05": ("truncated", 35), "c11": ("ok", 19), "c12": ("ok", 30),
        })
        self.assertEqual(self.report["rejected"], {
            "c06": "too_long", "c07": "unknown_role", "c08": "bad_order",
            "c09": "misplaced_system", "c10": "empty_message",
        })

    def test_2_rendered_text(self):
        self.assertEqual(self.report["examples"]["c05"]["text"], C05_TEXT)


if __name__ == "__main__":
    unittest.main()
