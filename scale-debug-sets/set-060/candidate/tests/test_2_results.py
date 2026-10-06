import unittest

from tests.mock_server import API_KEY, MockApiServer
from vecsync.runner import build_report


class TestResults(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = MockApiServer().start()
        cls.report = build_report(cls.server.url, API_KEY)

    @classmethod
    def tearDownClass(cls):
        cls.server.stop()

    def test_rejected_batch(self):
        self.assertEqual(self.report["batches"]["b5"], {
            "status": "http_error", "http_status": 400, "attempts": 1,
            "records": ["faq-20", "faq-21", "faq-22", "faq-23"],
        })

    def test_dimension_mismatch(self):
        self.assertEqual(self.report["batches"]["b4"], {
            "status": "dim_mismatch", "http_status": 200, "attempts": 1,
            "records": ["faq-16", "faq-17", "faq-18", "faq-19"],
        })

    def test_selected_records(self):
        self.assertEqual(self.report["selected"], [
            "faq-01", "faq-02", "faq-03", "faq-04", "faq-06", "faq-08", "faq-09", "faq-10",
            "faq-11", "faq-13", "faq-14", "faq-15", "faq-16", "faq-17", "faq-18", "faq-19",
            "faq-20", "faq-21", "faq-22", "faq-23", "faq-24", "faq-25",
        ])

    def test_ok_batches(self):
        batches = self.report["batches"]
        self.assertEqual({b: (batches[b]["status"], batches[b]["attempts"]) for b in ("b1", "b2", "b3", "b6")},
                         {"b1": ("ok", 1), "b2": ("ok", 3), "b3": ("ok", 2), "b6": ("ok", 1)})
        vectors = self.report["vectors"]
        self.assertEqual(sorted(vectors), [
            "faq-01", "faq-02", "faq-03", "faq-04", "faq-06", "faq-08", "faq-09", "faq-10",
            "faq-11", "faq-13", "faq-14", "faq-15", "faq-24", "faq-25",
        ])
        self.assertEqual(vectors["faq-01"], [27.0, 5.0, 44.0, 15.0])
        self.assertEqual(vectors["faq-02"][0], 30.0)
        self.assertEqual(vectors["faq-04"], [24.0, 5.0, 12.0, 11.0])


if __name__ == "__main__":
    unittest.main()
