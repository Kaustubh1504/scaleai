import unittest

from prelabel.reports import build_report


class TestModelSummary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()
        cls.models = cls.report["models"]

    def test_detr_totals(self):
        m = self.models["detr-v2"]
        self.assertEqual((m["tp"], m["fp"], m["fn"], m["precision"], m["recall"], m["f1"]),
                         (9, 3, 3, 0.75, 0.75, 0.75))

    def test_yolo_totals(self):
        m = self.models["yolo-s"]
        self.assertEqual((m["tp"], m["fp"], m["fn"], m["precision"], m["recall"], m["f1"]),
                         (10, 0, 2, 1.0, 0.833, 0.909))

    def test_auto_accept(self):
        self.assertEqual({k: v["auto_accept"] for k, v in self.models.items()}, {
            "detr-v2": ["img-01", "img-02", "img-04", "img-06", "img-08"],
            "yolo-s": ["img-01", "img-03", "img-04", "img-05", "img-07", "img-08", "img-09"],
        })

    def test_best_model(self):
        self.assertEqual(self.report["best_model"], "yolo-s")


if __name__ == "__main__":
    unittest.main()
