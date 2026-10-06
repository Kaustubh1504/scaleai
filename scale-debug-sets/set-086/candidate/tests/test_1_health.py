import unittest

from lbreplay.report import build_report


class TestHealth(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_backends_in_rotation(self):
        self.assertEqual(sorted(self.report["final_state"]), ["b01", "b02", "b03", "b04"])

    def test_transitions(self):
        self.assertEqual(self.report["transitions"], [[21000, "b03", "down"], [32000, "b03", "healthy"]])

    def test_final_state(self):
        self.assertEqual(self.report["final_state"],
                         {"b01": "healthy", "b02": "healthy", "b03": "healthy", "b04": "healthy"})


if __name__ == "__main__":
    unittest.main()
