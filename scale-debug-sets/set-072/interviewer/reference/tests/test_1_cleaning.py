import unittest

from voxsplit.reports import build_report


def ids_with(report, reason):
    return sorted(cid for cid, why in report["excluded"].items() if why == reason)


class TestCleaning(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_unknown_speaker_and_empty_transcripts(self):
        self.assertEqual(ids_with(self.report, "unknown_speaker"), ["C037"])
        self.assertEqual(ids_with(self.report, "no_transcript"), ["C033", "C038"])

    def test_consent_exclusions(self):
        self.assertEqual(ids_with(self.report, "no_consent"), ["C002", "C012", "C017", "C027"])

    def test_duration_exclusions(self):
        self.assertEqual(ids_with(self.report, "duration"), ["C011", "C022"])

    def test_duplicate_exclusions(self):
        self.assertEqual(ids_with(self.report, "duplicate"), ["C005", "C015", "C035"])


if __name__ == "__main__":
    unittest.main()
