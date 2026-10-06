import asyncio
import unittest

from embedindex.reports import build_report
from tests.mock_server import API_KEY, MockEmbeddingServer


async def no_wait(seconds):
    await asyncio.sleep(0)


class TestBatches(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = MockEmbeddingServer().start()
        cls.report = build_report(cls.server.url, API_KEY, sleep=no_wait)

    @classmethod
    def tearDownClass(cls):
        cls.server.stop()

    def test_batch_membership(self):
        docs = {b: r["docs"] for b, r in self.report["batches"].items()}
        self.assertEqual(docs, {
            "faq-01": ["f01", "f02", "f03"],
            "faq-02": ["f04", "f06", "f07"],
            "faq-03": ["f08", "f09"],
            "kb-01": ["k01", "k02", "k03"],
            "kb-02": ["k04", "k05", "k06"],
            "policies-01": ["p01", "p02", "p03"],
            "policies-02": ["p04"],
        })

    def test_batch_outcomes(self):
        outcomes = {b: (r["status"], r["http_status"], r["attempts"]) for b, r in self.report["batches"].items()}
        self.assertEqual(outcomes, {
            "faq-01": ("ok", 200, 1),
            "faq-02": ("ok", 200, 2),
            "faq-03": ("ok", 200, 1),
            "kb-01": ("ok", 200, 3),
            "kb-02": ("failed", 422, 1),
            "policies-01": ("failed", 503, 3),
            "policies-02": ("ok", 200, 1),
        })

    def test_vectors(self):
        self.maxDiff = None
        self.assertEqual(self.report["vectors"], {
            "f01": [0.5149, 0.1335, 0.1144, 0.839],
            "f02": [0.5251, 0.175, 0.0955, 0.8274],
            "f03": [0.478, 0.1487, 0.0956, 0.8604],
            "f04": [0.5597, 0.1544, 0.0772, 0.8105],
            "f06": [0.6356, 0.2311, 0.1445, 0.7223],
            "f07": [0.8296, 0.3111, 0.2074, 0.4148],
            "f08": [0.6322, 0.2371, 0.0988, 0.731],
            "f09": [0.9605, 0.2101, 0.1801, 0.03],
            "k01": [36.0, 11.0, 5.0, 64.0],
            "k02": [34.0, 12.0, 5.0, 88.0],
            "k03": [30.0, 13.0, 3.0, 37.0],
            "p04": [0.5175, 0.1606, 0.0535, 0.8388],
        })


if __name__ == "__main__":
    unittest.main()
