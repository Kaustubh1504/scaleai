def gold_ratings(ratings, items):
    return [r for r in ratings if items[r.item_id].gold is not None]


def compute_bias(gold, items, annotator_id, rubric):
    rows = [r for r in gold if r.annotator_id == annotator_id and items[r.item_id].rubric == rubric]
    if not rows:
        return 0.0
    return sum(r.score - items[r.item_id].gold for r in rows) / len(rows)


def bias_for(memo, gold, items, annotator_id, rubric):
    return memo.get_or_compute((annotator_id, rubric), lambda: compute_bias(gold, items, annotator_id, rubric))


# VERIFIED
def adjust(score, bias):
    """Remove an annotator's habitual lean, keeping the result on the 1-5 scale."""
    return min(5.0, max(1.0, score - bias))
