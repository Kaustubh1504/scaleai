from .aggregate import margin_of

MIN_ACCURACY = 0.7


def labeler_quality(calibration, pairs, active):
    """Accuracy on calibration pairs for every active labeler."""
    answered, correct = {}, {}
    for j in calibration:
        pair = pairs.get(j.pair_id)
        if pair is None or not pair.gold or not active.get(j.labeler_id):
            continue
        m = margin_of(j, pair)
        hit = (m > 0 and pair.gold == "A") or (m < 0 and pair.gold == "B")
        answered[j.labeler_id] = answered.get(j.labeler_id, 0) + 1
        correct[j.labeler_id] = correct.get(j.labeler_id, 0) + int(hit)
    table = {}
    for lab in sorted(l for l, is_active in active.items() if is_active):
        n = answered.get(lab, 0)
        acc = round(correct[lab] / n, 3) if n else None
        table[lab] = {"checks": n, "accuracy": acc, "excluded": acc is not None and acc < MIN_ACCURACY}
    return table
