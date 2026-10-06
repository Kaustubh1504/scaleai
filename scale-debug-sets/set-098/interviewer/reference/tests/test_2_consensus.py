import unittest

from quorum.reports import build_report


def res(status, label, agreement, votes):
    return {"status": status, "label": label, "agreement": agreement, "votes": votes}


class TestConsensus(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.queues = build_report()["queues"]

    def test_queue_names(self):
        self.assertEqual(list(self.queues), ["quality", "spam", "tox"])

    def test_tox_items(self):
        self.assertEqual(self.queues["tox"]["items"], {
            "T01": res("accepted", "toxic", 0.714, 3),
            "T02": res("escalated", "toxic", 0.5, 3),
            "T03": res("accepted", "threat", 0.75, 4),
            "T04": res("pending", None, None, 2),
        })

    def test_spam_items(self):
        self.assertEqual(self.queues["spam"]["items"], {
            "S01": res("accepted", "spam", 1.0, 2),
            "S02": res("escalated", "spam", 0.571, 3),
            "S03": res("accepted", "ham", 1.0, 3),
            "S04": res("accepted", "phishing", 0.75, 3),
        })

    def test_quality_items(self):
        self.assertEqual(self.queues["quality"]["items"], {
            "Q01": res("accepted", "good", 0.667, 3),
            "Q02": res("accepted", "fair", 0.667, 4),
            "Q03": res("escalated", "good", 0.375, 3),
            "Q04": res("accepted", "good", 1.0, 5),
            "Q05": res("pending", None, None, 2),
        })


if __name__ == "__main__":
    unittest.main()
