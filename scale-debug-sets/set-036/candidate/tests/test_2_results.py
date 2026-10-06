import unittest

from tests.helpers import run_against_mock
from tests.mock_server import embed


class TestResults(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server, cls.waits, cls.report = run_against_mock()

    @classmethod
    def tearDownClass(cls):
        cls.server.stop()

    def test_embedded_documents(self):
        self.assertEqual(self.report["embedded"], [
            "d01", "d02", "d03", "d04", "d05", "d06", "d07", "d08",
            "d13", "d14", "d15", "d16", "d17", "d18",
        ])

    def test_failed_batches(self):
        self.assertEqual(self.report["failed_batches"], [
            {"batch": 2, "status": 503, "doc_ids": ["d09", "d10", "d11", "d12"]},
        ])

    def test_vectors_stored_per_document(self):
        puts = {r["path"].rsplit("/", 1)[-1]: r["body"]["embedding"]
                for r in self.server.requests if r["method"] == "PUT"}
        self.assertEqual(puts["d08"], embed("Workers are paid weekly once their reviewed tasks pass quality checks."))
        self.assertEqual(puts["d13"], puts["d03"])

    def test_index_results(self):
        self.assertEqual(self.report["index"], {"stored": 13, "rejected": ["d07"]})


if __name__ == "__main__":
    unittest.main()
