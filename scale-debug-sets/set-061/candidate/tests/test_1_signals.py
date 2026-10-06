import unittest

from tripwire.report import build_report


class TestSignals(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()
        cls.rows = cls.report["annotators"]

    def test_active_annotators_only(self):
        self.assertEqual(
            sorted(self.rows),
            ["A01", "A02", "A03", "A04", "A05", "A06", "A07", "A08", "A09", "A12"],
        )

    def test_task_medians(self):
        self.assertEqual(
            self.report["tasks"],
            {
                "t1": {"submissions": 7, "median_s": 120.0},
                "t2": {"submissions": 7, "median_s": 112.5},
                "t3": {"submissions": 7, "median_s": 140.0},
                "t4": {"submissions": 6, "median_s": 110.0},
                "t5": {"submissions": 4, "median_s": 65.0},
            },
        )

    def test_timed_and_rushed_counts(self):
        got = {a: (r["submissions"], r["timed"], r["rushed"]) for a, r in self.rows.items()}
        self.assertEqual(got, {
            "A01": (5, 5, 0), "A02": (5, 3, 1), "A03": (4, 4, 2), "A04": (4, 4, 0),
            "A05": (4, 4, 2), "A06": (2, 2, 0), "A07": (3, 2, 0), "A08": (4, 4, 0),
            "A09": (0, 0, 0), "A12": (0, 0, 0),
        })

    def test_1_rush_rates(self):
        got = {a: r["rush_rate"] for a, r in self.rows.items() if r["timed"]}
        self.assertEqual(got, {
            "A01": 0.0, "A02": 33.3, "A03": 50.0, "A04": 0.0, "A05": 50.0,
            "A06": 0.0, "A07": 0.0, "A08": 0.0,
        })

    def test_2_shared_answer_counts(self):
        got = {a: r["shared_answers"] for a, r in self.rows.items() if r["shared_answers"]}
        self.assertEqual(got, {"A01": 1, "A02": 1, "A04": 4, "A08": 4})


if __name__ == "__main__":
    unittest.main()
