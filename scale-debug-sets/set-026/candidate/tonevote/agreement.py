from collections import Counter

from .models import AgreementRow


def agreement_table(annotations, results):
    agreed = {tid: r.label for tid, r in results.items() if r.status == "agreed"}
    seen, hits, skips = Counter(), Counter(), Counter()
    annotators = set()
    for ann in annotations:
        aid = ann.annotator_id
        annotators.add(aid)
        if ann.skipped:
            skips[aid] += 1
        if ann.task_id not in agreed:
            continue
        seen[aid] += 1
        if ann.label == agreed[ann.task_id]:
            hits[aid] += 1
    return {
        aid: AgreementRow(seen[aid], hits[aid] / seen[aid] if seen[aid] else None, skips[aid])
        for aid in sorted(annotators)
    }


def votes_by_annotator(annotations):
    return Counter(ann.annotator_id for ann in annotations if not ann.skipped)
