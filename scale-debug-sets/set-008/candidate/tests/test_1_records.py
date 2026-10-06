import unittest

from rosterload.report import build_report


class TestRecords(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = build_report()["records"]

    def test_accepted_emails(self):
        self.assertEqual(sorted(self.records), [
            "asha@lab.io", "ben@lab.io", "chen@lab.io", "femi@lab.io", "gita@lab.io",
            "ines@lab.io", "jon@lab.io", "kai@lab.io", "lena@lab.io", "pia@lab.io",
            "quinn@lab.io", "raj@lab.io", "tara@lab.io", "vik@lab.io", "wen@lab.io", "xia@lab.io",
        ])

    def test_winning_rows(self):
        got = {e: (r["name"], r["vendor"]) for e, r in self.records.items()
               if e in ("asha@lab.io", "ben@lab.io", "femi@lab.io", "gita@lab.io")}
        self.assertEqual(got, {
            "asha@lab.io": ("Asha R.", "vendor_b"),
            "ben@lab.io": ("Benjamin Ortiz", "vendor_c"),
            "femi@lab.io": ("Femi Ade", "vendor_b"),
            "gita@lab.io": ("Gita Shah", "vendor_a"),
        })

    def test_lineage(self):
        got = {e: self.records[e]["sources"] for e in ("asha@lab.io", "ben@lab.io", "jon@lab.io")}
        self.assertEqual(got, {
            "asha@lab.io": ["vendor_a:A-101", "vendor_b:B-201"],
            "ben@lab.io": ["vendor_a:A-102", "vendor_b:B-202", "vendor_c:C-307"],
            "jon@lab.io": ["vendor_a:A-110"],
        })

    def test_skills(self):
        got = {e: self.records[e]["skills"] for e in ("asha@lab.io", "ben@lab.io", "chen@lab.io", "femi@lab.io", "kai@lab.io")}
        self.assertEqual(got, {
            "asha@lab.io": ["python", "spark", "sql"],
            "ben@lab.io": ["nlp", "python", "sql"],
            "chen@lab.io": ["nlp", "python", "vision"],
            "femi@lab.io": ["audio", "nlp"],
            "kai@lab.io": [],
        })


if __name__ == "__main__":
    unittest.main()
