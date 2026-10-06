from collections import defaultdict

from .models import ModelScore, Status
from .parsing import parse_choice


def select_final(attempts):
    """Pick the attempt whose output gets graded."""
    best = None
    for att in attempts:
        if att.status in ("error", "timeout"):
            continue
        if best is None or att.attempt > best.attempt:
            best = att
    return best


def group_attempts(attempts):
    grouped = defaultdict(lambda: defaultdict(list))
    for att in attempts:
        grouped[att.model][att.item_id].append(att)
    return grouped


def score_model(model, items, by_item):
    score = ModelScore(model)
    for item in items:
        final = select_final(by_item.get(item.item_id, []))
        if final is None:
            score.failed.append(item.item_id)
            continue
        score.possible += item.weight
        choice = parse_choice(final.output)
        if choice is None:
            score.unparsed.append(item.item_id)
        elif choice == item.answer:
            score.correct.append(item.item_id)
            score.earned += item.weight
    return score
