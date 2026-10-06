import unittest

from sftfmt.reports import build_report


class TestRender(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.examples = build_report()["examples"]

    def test_rendered_text(self):
        self.assertEqual(self.examples["c01"]["text"],
                         "<|system|>\nYou are a helpful assistant.<|end|>\n"
                         "<|user|>\nWhat is the capital of Peru?<|end|>\n"
                         "<|assistant|>\nThe capital of Peru is Lima.<|end|>\n")

    def test_existing_system_prompt_kept(self):
        self.assertTrue(self.examples["c02"]["text"].startswith("<|system|>\nAnswer in one word.<|end|>\n<|user|>"))
        self.assertTrue(self.examples["c11"]["text"].startswith("<|system|>\nReply in French.<|end|>\n<|user|>"))

    def test_assistant_spans(self):
        self.assertEqual(self.examples["c03"]["spans"], [[106, 110], [161, 165]])
        text = self.examples["c09"]["text"]
        self.assertEqual([text[s:e] for s, e in self.examples["c09"]["spans"]], ["4.", "9.", "2.5."])

    def test_truncation(self):
        got = {cid: (self.examples[cid]["tokens"], self.examples[cid]["turns_dropped"]) for cid in ("c07", "c09", "c13")}
        self.assertEqual(got, {"c07": (20, 2), "c09": (32, 0), "c13": (26, 2)})


if __name__ == "__main__":
    unittest.main()
