from collections import Counter
from pathlib import Path

from .gold import quality_table
from .loader import load_annotations, load_annotators, load_tasks
from .voting import mark_blocked, resolve

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def summarize(results):
    resolved = [r for r in results.values() if r.status == "resolved"]
    counts = Counter(r.label for r in results.values())
    needs = sorted(r.task_id for r in results.values() if r.status == "needs_more_votes")
    disputed = min(resolved, key=lambda r: (r.confidence, r.task_id)).task_id if resolved else None
    return {"label_counts": dict(counts), "needs_more_votes": needs, "most_disputed": disputed}


def build_report(data_dir=None):
    data_dir = Path(data_dir or DATA_DIR)
    registry = load_annotators(data_dir / "annotators.json")
    task_ids, gold = load_tasks(data_dir / "tasks.csv")
    annotations = load_annotations(data_dir / "annotations.csv", registry)
    table = mark_blocked(quality_table(annotations, gold, registry))
    results = resolve(task_ids, annotations, gold, table)
    return {
        "annotators": {
            aid: {"accuracy": round(row.accuracy, 3), "gold_answered": row.gold_answered, "blocked": row.blocked}
            for aid, row in table.items()
        },
        "consensus": {
            tid: {"status": r.status, "label": r.label, "confidence": r.confidence, "votes": r.votes}
            for tid, r in results.items()
        },
        "summary": summarize(results),
    }
