import unittest

from tests.helpers import run_against_mock


class TestReport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server, cls.report = run_against_mock()

    def test_batches_and_skips(self):
        self.assertEqual(self.report["batches"], ["faq/1", "faq/2", "legal/1", "news/1", "product/1", "support/1"])
        self.assertEqual(self.report["skipped"], {
            "unknown_collection": ["mk-01"],
            "disabled_collection": ["ar-01", "ar-02"],
            "blank_text": ["faq-08"],
        })

    def test_failed_batch_reported(self):
        self.assertEqual(self.report["failures"].get("support/1"), "input_too_long")
        self.assertFalse(any(d.startswith("sp-") for d in self.report["embedded"]))

    def test_faq_embeddings(self):
        faq = {d: v["norm"] for d, v in self.report["embedded"].items() if d.startswith("faq-")}
        self.assertEqual(faq, {
            "faq-01": 12.8841, "faq-02": 11.9583, "faq-03": 12.6095, "faq-04": 9.6954,
            "faq-05": 12.4499, "faq-06": 15.0997, "faq-07": 11.619,
        })


if __name__ == "__main__":
    unittest.main()
