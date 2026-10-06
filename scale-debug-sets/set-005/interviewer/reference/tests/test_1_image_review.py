import unittest

from boxqa.reports import build_report


def row(tp, fp, fn, recall):
    return {"tp": tp, "fp": fp, "fn": fn, "recall": recall}


EXPECTED_IMAGES = {
    "img_01/alice": row(2, 0, 0, 1.0),
    "img_01/bob": row(2, 0, 0, 1.0),
    "img_01/chen": row(1, 1, 1, 0.5),
    "img_02/alice": row(2, 0, 0, 1.0),
    "img_02/bob": row(1, 0, 1, 0.5),
    "img_02/chen": row(1, 0, 1, 0.5),
    "img_03/alice": row(0, 1, 1, 0.0),
    "img_03/bob": row(1, 0, 0, 1.0),
    "img_03/chen": row(1, 0, 0, 1.0),
    "img_04/alice": row(1, 0, 1, 0.5),
    "img_04/bob": row(2, 1, 0, 1.0),
    "img_05/alice": row(3, 0, 0, 1.0),
    "img_05/bob": row(2, 0, 1, 0.667),
    "img_05/chen": row(3, 1, 0, 1.0),
    "img_06/bob": row(0, 1, 0, 1.0),
}


class TestImageReview(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_exact_box_is_a_match(self):
        self.assertEqual(self.report["images"]["img_03/bob"], row(1, 0, 0, 1.0))

    def test_flagged_for_re_review(self):
        self.assertEqual(self.report["flagged"], [
            "img_01/chen", "img_02/bob", "img_02/chen", "img_03/alice", "img_04/alice", "img_05/bob",
        ])

    def test_per_image_counts(self):
        self.maxDiff = None
        self.assertEqual(self.report["images"], EXPECTED_IMAGES)


if __name__ == "__main__":
    unittest.main()
