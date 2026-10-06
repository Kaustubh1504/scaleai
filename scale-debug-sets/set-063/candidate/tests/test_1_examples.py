import unittest

from turnsmith.export import build_dataset

SYSTEM = {"role": "system", "content": "You are a helpful support assistant."}


def u(text):
    return {"role": "user", "content": text}


def a(text):
    return {"role": "assistant", "content": text}


class TestExamples(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = build_dataset()
        cls.examples = cls.data["examples"]

    def test_example_ids(self):
        self.assertEqual(sorted(self.examples), ["c01", "c02", "c03", "c05", "c08", "c09", "c10"])

    def test_merged_and_trimmed_messages(self):
        self.assertEqual(self.examples["c02"]["messages"], [
            SYSTEM, u("hi\nmy order is late"), a("Sorry about that, let me check the tracking number for you."),
        ])
        self.assertEqual(self.examples["c05"]["messages"], [
            SYSTEM, u("I want to return a jacket."), a("Sure. Use the Returns page and print the label."),
        ])
        self.assertEqual(self.examples["c08"]["messages"], [
            SYSTEM,
            u("How do I download my invoices as CSV?"),
            a("Use the export button on the invoices page."),
            u("And for last year?"),
            a("Change the year filter first and then export."),
        ])

    def test_token_counts(self):
        got = {cid: ex["tokens"] for cid, ex in self.examples.items()}
        self.assertEqual(got, {"c01": 33, "c02": 34, "c03": 59, "c05": 33, "c08": 54, "c09": 35, "c10": 47})

    def test_truncated_examples(self):
        self.assertEqual(self.examples["c03"]["dropped_messages"], 2)
        self.assertEqual(self.examples["c03"]["messages"][1], u("Can I return it if it arrives after my trip?"))
        self.assertEqual(self.examples["c10"]["dropped_messages"], 2)
        self.assertEqual(self.examples["c10"]["messages"], [
            SYSTEM,
            u("How long to Toronto?"),
            a("Usually five to seven business days."),
            u("Is there a tracking link?"),
            a("It is in your confirmation email."),
        ])

    def test_example_tags(self):
        got = {cid: ex["tags"] for cid, ex in self.examples.items()}
        self.assertEqual(got, {
            "c01": ["billing"], "c02": ["general"], "c03": ["shipping", "returns"],
            "c05": ["returns"], "c08": ["coding", "billing"], "c09": ["general"], "c10": ["shipping"],
        })


if __name__ == "__main__":
    unittest.main()
