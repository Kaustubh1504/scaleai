import unittest

from tests.harness import SyncRun


class TestSync(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.run_ = SyncRun()
        cls.report = cls.run_.report()
        cls.outcomes = cls.report["outcomes"]

    @classmethod
    def tearDownClass(cls):
        cls.run_.stop()

    def test_unchanged_policies_skipped(self):
        policies = {k: v for k, v in self.outcomes.items() if k.startswith("p")}
        self.assertEqual(policies, {"p01": "skipped", "p02": "skipped", "p03": "skipped",
                                    "p04": "embedded", "p05": "skipped", "p07": "embedded"})

    def test_faq_embedded(self):
        faq = sorted(k for k, v in self.outcomes.items() if k.startswith("f") and v == "embedded")
        self.assertEqual(faq, ["f01", "f02", "f03", "f04", "f06", "f07", "f08"])

    def test_vectors_matched_to_documents(self):
        self.assertEqual(self.report["embeddings"], {
            "f01": [27.0, 6.0], "f02": [34.0, 7.0], "f03": [41.0, 8.0], "f04": [36.0, 8.0],
            "f06": [36.0, 7.0], "f07": [25.0, 5.0], "f08": [30.0, 4.0],
            "p04": [35.0, 6.0], "p07": [32.0, 5.0],
            "x01": [23.0, 4.0], "x02": [23.0, 4.0], "x03": [24.0, 3.0],
        })

    def test_retired_and_blank_documents_not_processed(self):
        self.assertFalse({"p06", "x06", "f05", "x08"} & set(self.outcomes))

    def test_index_entries_to_delete(self):
        self.assertEqual(self.report["to_delete"], ["p06", "p41", "p42", "p43", "p88"])


if __name__ == "__main__":
    unittest.main()
