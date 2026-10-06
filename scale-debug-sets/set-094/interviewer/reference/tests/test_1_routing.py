import unittest

from hitlroute.reports import build_report


def routes(decisions, prefix):
    return {k: (v["route"], v["reason"]) for k, v in decisions.items() if k.startswith(prefix)}


class TestRouting(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.decisions = build_report()["decisions"]

    def test_every_prediction_routed(self):
        self.assertEqual(len(self.decisions), 32)

    def test_guard_v3_routing(self):
        self.maxDiff = None
        self.assertEqual(routes(self.decisions, "I"), {
            "I01": ("auto", "confident"),
            "I02": ("expert", "low_confidence"),
            "I03": ("expert", "low_confidence"),
            "I04": ("expert", "sensitive"),
            "I05": ("expert", "low_confidence"),
            "I06": ("auto", "confident"),
            "I07": ("expert", "low_confidence"),
            "I08": ("crowd", "low_confidence"),
            "I09": ("auto", "confident"),
            "I10": ("expert", "low_confidence"),
            "I11": ("expert", "sensitive"),
            "I12": ("expert", "no_confidence"),
            "I13": ("expert", "flagged"),
            "I14": ("expert", "unknown_label"),
            "I15": ("crowd", "low_confidence"),
            "I16": ("expert", "low_confidence"),
            "I17": ("expert", "low_confidence"),
            "I18": ("expert", "low_confidence"),
            "I19": ("expert", "low_confidence"),
            "I20": ("expert", "low_confidence"),
        })

    def test_guard_mini_routing(self):
        self.assertEqual(routes(self.decisions, "M"), {
            "M01": ("auto", "confident"),
            "M02": ("auto", "confident"),
            "M03": ("auto", "confident"),
            "M04": ("auto", "confident"),
            "M05": ("crowd", "low_confidence"),
            "M06": ("auto", "confident"),
            "M07": ("crowd", "flagged"),
        })

    def test_legacy_model_routing(self):
        self.assertEqual(routes(self.decisions, "L"), {
            "L01": ("crowd", "legacy_model"),
            "L02": ("crowd", "legacy_model"),
            "L03": ("expert", "low_confidence"),
            "L04": ("crowd", "legacy_model"),
            "L05": ("crowd", "low_confidence"),
        })


if __name__ == "__main__":
    unittest.main()
