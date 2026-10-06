from dataclasses import dataclass

from .matching import greedy_match

MIN_RECALL = 0.8


@dataclass
class ImageResult:
    image_id: str
    annotator: str
    tp: int
    fp: int
    fn: int

    @property
    def recall(self):
        total = self.tp + self.fn
        return self.tp / total if total else 1.0

    @property
    def flagged(self):
        return self.recall < MIN_RECALL


def evaluate(gt_by_image, preds_by_key):
    results = []
    for (image_id, annotator), preds in sorted(preds_by_key.items()):
        gts = gt_by_image.get(image_id, [])
        matched_pred, matched_gt = set(), set()
        for i, j in greedy_match(preds, gts):
            matched_pred.add(i)
            matched_gt.add(j)
        results.append(ImageResult(
            image_id=image_id,
            annotator=annotator,
            tp=len(matched_gt),
            fp=len(preds) - len(matched_pred),
            fn=len(gts) - len(matched_gt),
        ))
    return results
