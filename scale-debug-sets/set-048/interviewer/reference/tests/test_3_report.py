import unittest

from splitkit.reports import build_report


class TestReport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_split_members(self):
        self.maxDiff = None
        self.assertEqual(self.report["splits"], {
            "train": ["S-013", "S-014", "S-015", "S-016", "S-017", "S-018",
                      "S-027", "S-028", "S-029", "S-030", "S-031", "S-032"],
            "val": ["S-005", "S-006", "S-009", "S-011", "S-012", "S-023", "S-024"],
            "test": ["S-001", "S-002", "S-003", "S-004", "S-007", "S-008", "S-019", "S-020"],
        })

    def test_capped(self):
        self.assertEqual(self.report["capped"], ["S-021", "S-022", "S-025", "S-026", "S-033"])

    def test_label_counts(self):
        self.assertEqual(self.report["label_counts"], {
            "train": {"bird": 4, "cat": 4, "dog": 4},
            "val": {"bird": 2, "cat": 3, "dog": 2},
            "test": {"bird": 1, "cat": 3, "dog": 4},
        })


if __name__ == "__main__":
    unittest.main()
