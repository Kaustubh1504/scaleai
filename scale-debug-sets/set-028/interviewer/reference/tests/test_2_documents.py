import unittest

from embedq.reports import build_report
from tests.mock_server import API_KEY, MockEmbeddingServer

DOC_IDS = ["d01", "d02", "d03", "d04", "d05", "d07", "d08", "d09",
           "d10", "d11", "d12", "d13", "d14", "d15", "d16"]


def ok(dims):
    return {"status": "ok", "dims": dims}


def failed(http_status, reason):
    return {"status": "failed", "http_status": http_status, "reason": reason}


class TestDocuments(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        async def no_sleep(seconds):
            return None

        cls.server = MockEmbeddingServer().start()
        cls.docs = build_report(cls.server.url, API_KEY, sleep=no_sleep)["documents"]

    @classmethod
    def tearDownClass(cls):
        cls.server.stop()

    def test_documents_listed(self):
        self.assertEqual(sorted(self.docs), DOC_IDS)

    def test_embed_s(self):
        self.maxDiff = None
        expected = {d: ok(4) for d in DOC_IDS}
        expected.update({d: failed(400, "rejected") for d in ("d09", "d11", "d12")})
        self.assertEqual({d: row["embed-s"] for d, row in self.docs.items()}, expected)

    def test_embed_l(self):
        self.maxDiff = None
        expected = {d: ok(8) for d in DOC_IDS}
        expected.update({d: failed(None, "invalid_response") for d in ("d01", "d02", "d03", "d04", "d10")})
        self.assertEqual({d: row["embed-l"] for d, row in self.docs.items()}, expected)


if __name__ == "__main__":
    unittest.main()
