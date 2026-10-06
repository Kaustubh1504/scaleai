import unittest

from labelbatch.reports import build_report
from tests.mock_server import API_KEY, MockBatchServer


def row(shard, status, label=None, score=None):
    return {"shard": shard, "status": status, "label": label, "score": score}


class TestResults(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = MockBatchServer().start()
        cls.requests = build_report(cls.server.url, API_KEY)["requests"]

    @classmethod
    def tearDownClass(cls):
        cls.server.stop()

    def shard(self, shard_id):
        return {rid: r for rid, r in self.requests.items() if r["shard"] == shard_id}

    def test_shard_s1(self):
        self.assertEqual(self.shard("S1"), {
            "R01": row("S1", "labeled", "cat", 0.95),
            "R02": row("S1", "labeled", "dog", 0.88),
            "R03": row("S1", "needs_review", "cat", 0.41),
        })

    def test_failed_shard_s4(self):
        self.assertEqual(self.shard("S4"), {"R14": row("S4", "failed"), "R15": row("S4", "failed")})

    def test_3_shard_s2_all_pages(self):
        self.maxDiff = None
        self.assertEqual(self.shard("S2"), {
            "R04": row("S2", "labeled", "dog", 0.91),
            "R05": row("S2", "labeled", "bird", 0.77),
            "R06": row("S2", "labeled", "cat", 0.83),
            "R07": row("S2", "needs_review", "dog", 0.52),
            "R08": row("S2", "labeled", "bird", 0.99),
            "R09": row("S2", "labeled", "cat", 0.74),
            "R10": row("S2", "labeled", "dog", 0.86),
        })

    def test_4_shard_s3_review_threshold(self):
        self.assertEqual(self.shard("S3"), {
            "R11": row("S3", "labeled", "bird", 0.93),
            "R12": row("S3", "labeled", "cat", 0.7),
            "R13": row("S3", "needs_review", "dog", 0.69),
        })

    def test_5_shard_s5(self):
        self.assertEqual(self.shard("S5"), {
            "R16": row("S5", "labeled", "bird", 0.81),
            "R17": row("S5", "labeled", "cat", 0.97),
            "R18": row("S5", "skipped"),
            "R19": row("S5", "needs_review", "dog", 0.6),
            "R20": row("S5", "skipped"),
        })


if __name__ == "__main__":
    unittest.main()
