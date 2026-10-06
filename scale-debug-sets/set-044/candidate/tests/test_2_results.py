import unittest

from embedclient.report import build_report
from tests.mock_server import API_KEY, MockEmbeddingServer


class TestResults(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = MockEmbeddingServer().start()
        cls.report = build_report(cls.server.url, API_KEY)

    @classmethod
    def tearDownClass(cls):
        cls.server.stop()

    def test_batches(self):
        self.assertEqual(self.report["batches"], {
            "b1": ["d01", "d02", "d03"], "b2": ["d04", "d05", "d07"], "b3": ["d08", "d09", "d10"],
            "b4": ["d11", "d12", "d13"], "b5": ["d14", "d15", "d16"], "b6": ["d17", "d18", "d19"],
            "b7": ["d20"],
        })

    def test_vectors(self):
        vectors = self.report["vectors"]
        self.assertEqual(sorted(vectors), ["d01", "d02", "d03", "d04", "d05", "d07", "d08", "d09", "d10",
                                           "d14", "d15", "d16", "d20"])
        self.assertEqual(vectors["d01"], [39.0, 7.0, 13.0])
        self.assertEqual(vectors["d03"], [47.0, 9.0, 15.0])
        self.assertEqual(vectors["d20"], [38.0, 5.0, 13.0])

    def test_failed_batches(self):
        self.assertEqual(self.report["failed"], {"b4": "HTTP 503", "b6": "HTTP 400"})


if __name__ == "__main__":
    unittest.main()
