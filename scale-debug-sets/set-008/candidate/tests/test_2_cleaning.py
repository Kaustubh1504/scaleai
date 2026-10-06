import unittest

from rosterload.report import build_report


class TestCleaning(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_rejected_rows(self):
        got = [(r["file"], r["row"]) for r in self.report["rejected"]]
        self.assertEqual(got, [
            ("vendor_a.csv", 4), ("vendor_a.csv", 5), ("vendor_a.csv", 8),
            ("vendor_b.csv", 5), ("vendor_b.csv", 6), ("vendor_b.csv", 7),
            ("vendor_c.json", 4), ("vendor_c.json", 6),
        ])

    def test_notes(self):
        got = {e: r["notes"] for e, r in self.report["records"].items() if r["notes"]}
        self.assertEqual(got, {
            "lena@lab.io": ["name_from_email"],
            "raj@lab.io": ["rate_missing"],
            "tara@lab.io": ["name_from_email"],
        })

    def test_rates(self):
        self.maxDiff = None
        got = {e: r["hourly_rate"] for e, r in self.report["records"].items()}
        self.assertEqual(got, {
            "asha@lab.io": 24.0, "ben@lab.io": 32.0, "chen@lab.io": 26.0, "femi@lab.io": 27.0,
            "gita@lab.io": 28.0, "ines@lab.io": 24.0, "jon@lab.io": 35.0, "kai@lab.io": 19.5,
            "lena@lab.io": 21.0, "pia@lab.io": 0.0, "quinn@lab.io": 23.0, "raj@lab.io": None,
            "tara@lab.io": 22.0, "vik@lab.io": 25.0, "wen@lab.io": 24.0, "xia@lab.io": 21.0,
        })


if __name__ == "__main__":
    unittest.main()
