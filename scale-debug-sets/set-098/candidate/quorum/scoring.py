from collections import defaultdict

CONTESTED_BELOW = 0.8


def annotator_agreement(results, votes):
    """Share of each annotator's votes on settled items that match the consensus label."""
    matched, total = defaultdict(int), defaultdict(int)
    for vote in votes:
        result = results.get(vote.item_id)
        if result is None or result.label is None:
            continue
        total[vote.annotator_id] += 1
        if vote.label == result.label:
            matched[vote.annotator_id] += 1
    return {aid: round(matched[aid] / total[aid], 3) for aid in sorted(total)}


def contested(results):
    return sorted(r.item_id for r in results.values()
                  if r.status == "accepted" and r.agreement < CONTESTED_BELOW or r.expert_dissent)
