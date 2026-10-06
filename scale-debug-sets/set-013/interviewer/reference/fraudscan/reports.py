from pathlib import Path

from .copying import copy_tasks
from .loader import load_registry, load_submissions
from .models import AnnotatorReport
from .timing import flag_speeders, is_fast

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def build_report(data_dir=None):
    data_dir = Path(data_dir or DATA_DIR)
    registry = load_registry(data_dir / "annotators.csv")
    submissions, rejected = load_submissions(data_dir / "submissions.csv", registry)

    table = {}
    for sub in submissions:
        row = table.setdefault(sub.annotator_id, AnnotatorReport(sub.annotator_id))
        row.submissions += 1
        row.fast += is_fast(sub)
    flag_speeders(table)
    copies = copy_tasks(submissions)
    for names in copies.values():
        for name in names:
            table[name].flags.add("copying")

    return {
        "annotators": {
            aid: {"submissions": r.submissions, "fast_ratio": r.fast_ratio, "flags": sorted(r.flags)}
            for aid, r in sorted(table.items())
        },
        "summary": {
            "flagged": sorted(aid for aid, r in table.items() if r.flags),
            "copy_tasks": copies,
            "rejected": sorted(rejected),
        },
    }
