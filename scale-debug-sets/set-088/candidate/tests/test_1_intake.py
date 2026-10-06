import unittest

from batchsched.report import build_schedule

ACCEPTED = ["C01", "C02", "C03", "C04", "G01", "G02", "G03", "I01", "I02", "I03",
            "L01", "M01", "M02", "M03", "M04"]


class TestIntake(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = build_schedule()
        cls.intake = cls.result["intake"]

    def test_accepted_and_rejected(self):
        self.assertEqual(sorted(self.intake), ACCEPTED)
        self.assertEqual(self.result["rejected"], {"X01": "unknown_pool"})

    def test_parsed_fields(self):
        got = {jid: (row["pool"], row["priority"], row["duration"]) for jid, row in self.intake.items()}
        self.assertEqual(got, {
            "C01": ("cpu", 2, 40), "C02": ("cpu", 5, 20), "C03": ("cpu", 3, 30), "C04": ("cpu", 1, 10),
            "G01": ("gpu", 3, 30), "G02": ("gpu", 2, 10), "G03": ("gpu", 4, 20),
            "I01": ("io", 3, 15), "I02": ("io", 3, 10), "I03": ("io", 3, 10),
            "L01": ("cpu", 3, 60),
            "M01": ("mem", 3, 50), "M02": ("mem", 3, 70), "M03": ("mem", 1, 30), "M04": ("mem", 2, 20),
        })

    def test_1_dependencies(self):
        deps = {jid: row["depends_on"] for jid, row in self.intake.items() if row["depends_on"]}
        self.assertEqual(deps, {"G03": ["G01"], "I02": ["I01"], "M04": ["M02", "M03"]})


if __name__ == "__main__":
    unittest.main()
