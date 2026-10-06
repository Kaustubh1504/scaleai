import unittest

from vendorfeed.reports import build_report

FIELDS = {
    "T001": ("acme", "a.lee@acme.io", "2026-03-02T09:00"),
    "T002": ("brightlabel", "r.diaz@brightlabel.com", "2026-03-04T10:00"),
    "T003": ("cortex", "j.ruiz@cortex.ai", "2026-03-05T12:00"),
    "T005": ("acme", "a.lee@acme.io", "2026-03-02T10:00"),
    "T006": ("acme", "m.khan@acme.io", "2026-03-02T10:05"),
    "T009": ("acme", "a.lee@acme.io", "2026-03-03T08:30"),
    "T012": ("acme", "m.khan@acme.io", "2026-03-03T09:10"),
    "T014": ("brightlabel", "k.osei@brightlabel.com", "2026-03-02T11:00"),
    "T016": ("brightlabel", "k.osei@brightlabel.com", "2026-03-04T10:30"),
    "T017": ("brightlabel", "k.osei@brightlabel.com", "2026-03-04T10:40"),
    "T018": ("brightlabel", "r.diaz@brightlabel.com", "2026-03-04T11:00"),
    "T019": ("brightlabel", "r.diaz@brightlabel.com", "2026-03-04T11:10"),
    "T021": ("brightlabel", "r.diaz@brightlabel.com", "2026-03-04T11:30"),
    "T022": ("brightlabel", "r.diaz@brightlabel.com", "2026-03-05T09:00"),
    "T024": ("cortex", "s.ito@cortex.ai", "2026-03-05T12:10"),
    "T025": ("cortex", "s.ito@cortex.ai", "2026-03-05T12:20"),
    "T026": ("cortex", "s.ito@cortex.ai", "2026-03-05T12:30"),
    "T027": ("cortex", "j.ruiz@cortex.ai", "2026-03-05T12:40"),
    "T029": ("cortex", "j.ruiz@cortex.ai", "2026-03-06T08:00"),
    "T030": ("cortex", "s.ito@cortex.ai", "2026-03-06T08:10"),
}


class TestRecords(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = build_report()["records"]

    def test_record_ids(self):
        self.assertEqual(sorted(self.records), sorted(list(FIELDS) + ["T008", "T015"]))

    def test_record_fields(self):
        self.maxDiff = None
        got = {tid: (r["vendor"], r["email"], r["submitted"]) for tid, r in self.records.items() if tid in FIELDS}
        self.assertEqual(got, FIELDS)

    def test_same_time_submissions(self):
        got = {tid: (self.records[tid]["vendor"], self.records[tid]["email"]) for tid in ("T008", "T015")}
        self.assertEqual(got, {
            "T008": ("acme", "j.ruiz@acme.io"),
            "T015": ("brightlabel", "r.diaz@brightlabel.com"),
        })

    def test_merged_tags(self):
        self.maxDiff = None
        merged = ("T001", "T002", "T003", "T008", "T009", "T012", "T015")
        self.assertEqual({tid: self.records[tid]["tags"] for tid in merged}, {
            "T001": ["sentiment", "short"],
            "T002": ["sarcasm", "sentiment"],
            "T003": ["long", "sentiment"],
            "T008": ["sarcasm", "sentiment"],
            "T009": ["long", "short"],
            "T012": ["sarcasm", "sentiment", "short"],
            "T015": ["long", "short"],
        })


if __name__ == "__main__":
    unittest.main()
