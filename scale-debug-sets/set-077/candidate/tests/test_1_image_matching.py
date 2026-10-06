import unittest

from prelabel.reports import build_report


def c(tp, fp, fn):
    return {"tp": tp, "fp": fp, "fn": fn}


class TestImageMatching(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.images = build_report()["images"]

    def _model(self, model):
        prefix = model + "/"
        return {k[len(prefix):]: v for k, v in self.images.items() if k.startswith(prefix)}

    def test_models_and_images(self):
        self.assertEqual(sorted({k.split("/")[0] for k in self.images}), ["detr-v2", "yolo-s"])
        self.assertEqual(len(self.images), 20)

    def test_detr_images(self):
        self.maxDiff = None
        self.assertEqual(self._model("detr-v2"), {
            "img-01": c(1, 0, 0), "img-02": c(2, 0, 0), "img-03": c(0, 1, 1), "img-04": c(1, 0, 0),
            "img-05": c(1, 0, 1), "img-06": c(2, 0, 0), "img-07": c(1, 1, 0), "img-08": c(1, 0, 0),
            "img-09": c(0, 0, 1), "img-10": c(0, 1, 0),
        })

    def test_yolo_images(self):
        self.maxDiff = None
        self.assertEqual(self._model("yolo-s"), {
            "img-01": c(1, 0, 0), "img-02": c(1, 0, 1), "img-03": c(1, 0, 0), "img-04": c(1, 0, 0),
            "img-05": c(2, 0, 0), "img-06": c(1, 0, 1), "img-07": c(1, 0, 0), "img-08": c(1, 0, 0),
            "img-09": c(1, 0, 0), "img-10": c(0, 0, 0),
        })


if __name__ == "__main__":
    unittest.main()
