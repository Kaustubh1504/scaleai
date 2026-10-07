
NEUTRAL = 4
TIE_BAND = 0.5
MIN_VOTES = 2


# VERIFIED
def a_margin(rating, left_is_a):
    """Ratings run 1 (left much better) .. 7 (right much better). Positive margin favours A."""
    return NEUTRAL - rating if left_is_a else rating - NEUTRAL


# VERIFIED
def verdict_for(margin):
    if abs(margin) < TIE_BAND:
        return "tie"
    return "A" if margin > 0 else "B"


def margin_of(judgement, pair):
    left_is_a = judgement.left_model == pair.model_a
    return a_margin(judgement.rating, left_is_a)


def aggregate(judgements, pairs, counted_labelers):
    votes = {pid: [] for pid, p in pairs.items() if not p.gold}
    for j in judgements:
        if j.pair_id in votes and j.labeler_id in counted_labelers:
            votes[j.pair_id].append(margin_of(j, pairs[j.pair_id]))
    results = {}
    for pid in sorted(votes):
        margins = votes[pid]
        if len(margins) < MIN_VOTES:
            results[pid] = {"votes": len(margins), "margin": None, "verdict": "insufficient"}
            continue
        avg = sum(margins) / len(margins)
        results[pid] = {"votes": len(margins), "margin": round(avg, 2), "verdict": verdict_for(avg)}
    return results
