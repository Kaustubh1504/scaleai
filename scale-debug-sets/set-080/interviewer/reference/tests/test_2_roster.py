import unittest

from rosterflow.reports import build_report


def c(name, country, hours, skills, sources):
    return {"name": name, "country": country, "hours": hours, "skills": skills, "sources": sources}


EXPECTED = {
    "ana@x.io": c("Ana Ruiz", "ES", 30, ["python", "spark", "sql"], ["vendor_a", "vendor_b"]),
    "cara@x.io": c("Cara Diaz", "MX", 40, ["labeling", "qa"], ["vendor_b", "vendor_c"]),
    "dev@x.io": c("Dev Patel", "IN", 40, ["python"], ["vendor_a"]),
    "eli@x.io": c("Eli Moor", "DE", 40, ["go", "rust"], ["vendor_c"]),
    "fay@x.io": c("Fay Wong", "HK", 12, [], ["vendor_b"]),
    "gus@x.io": c("Gus Berg", "SE", 35, ["python"], ["vendor_a"]),
    "kim@x.io": c("Kim Lee", "KR", 18, ["excel", "sql"], ["vendor_a", "vendor_b"]),
    "mia@x.io": c("Mia Novak", "CZ", 30, ["python", "qa"], ["vendor_b", "vendor_c"]),
    "noa@x.io": c("Noa Levi", "IL", 20, ["nlp", "python"], ["vendor_a"]),
    "raj@x.io": c("Raj N.", "IN", 50, ["ml", "python", "spark", "sql"], ["vendor_b", "vendor_c"]),
    "tia@x.io": c("Tia Moss", "AU", 8, ["ml"], ["vendor_b"]),
    "uma@x.io": c("Uma Rao", "IN", 30, ["ml", "python"], ["vendor_b"]),
    "wes@x.io": c("Wes Kim", "KR", 22, ["go", "python"], ["vendor_c"]),
    "xan@x.io": c("Xan Ford", "US", 60, ["sql"], ["vendor_c"]),
    "zoe@x.io": c("Zoe Park", "NZ", 16, [], ["vendor_c"]),
}


class TestRoster(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_members(self):
        self.assertEqual(sorted(self.report["roster"]), sorted(EXPECTED))

    def test_duplicates(self):
        self.assertEqual(self.report["duplicates"], 6)

    def test_records(self):
        self.maxDiff = None
        self.assertEqual(self.report["roster"], EXPECTED)


if __name__ == "__main__":
    unittest.main()
