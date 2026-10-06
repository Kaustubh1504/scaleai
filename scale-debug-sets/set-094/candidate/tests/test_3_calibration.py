import unittest

from hitlroute.reports import build_report


class TestCalibration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.calibration = build_report()["calibration"]

    def test_models_listed(self):
        self.assertEqual(list(self.calibration["models"]), ["guard-mini", "guard-v1", "guard-v3"])

    def test_model_calibration(self):
        self.assertEqual(self.calibration["models"], {
            "guard-mini": {"reviews": 6, "agreement": 0.667, "mean_confidence": 0.7, "gap": 0.033},
            "guard-v1": {"reviews": 4, "agreement": 0.5, "mean_confidence": 0.922, "gap": 0.422},
            "guard-v3": {"reviews": 9, "agreement": 0.556, "mean_confidence": 0.791, "gap": 0.236},
        })

    def test_label_confusions(self):
        self.assertEqual(self.calibration["confusions"], {
            "adult": "clean",
            "clean": None,
            "graphic_violence": None,
            "harassment": "clean",
            "hate_speech": "harassment",
            "off_topic": None,
            "promo": "off_topic",
            "spam": "low_quality",
        })


if __name__ == "__main__":
    unittest.main()
