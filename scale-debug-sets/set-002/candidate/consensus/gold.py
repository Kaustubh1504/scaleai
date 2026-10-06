from collections import Counter

from .models import QualityRow

PRIOR = 0.5


def gold_rates(annotations, gold):
    answered, correct = Counter(), Counter()
    for ann in annotations:
        expected = gold.get(ann.task_id)
        if expected is None:
            continue
        answered[ann.annotator_id] += 1
        if ann.label == expected:
            correct[ann.annotator_id] += 1
    rates = {aid: correct[aid] / n for aid, n in answered.items()}
    return rates, answered


def quality_table(annotations, gold, registry):
    rates, answered = gold_rates(annotations, gold)
    table = {}
    for aid in sorted(registry):
        if not registry[aid].active:
            continue
        table[aid] = QualityRow(accuracy=rates.get(aid) or PRIOR, gold_answered=answered[aid])
    return table
