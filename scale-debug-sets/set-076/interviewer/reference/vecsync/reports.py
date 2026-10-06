from collections import Counter
from pathlib import Path

from .index import coverage
from .models import REQUEUE_STATUSES, BatchStatus
from .runner import run

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def build_report(base_url, api_key, data_dir=None, sleep=None):
    outcome = run(base_url, api_key, data_dir or DATA_DIR, sleep=sleep)
    results = outcome.results
    counts = Counter(r.status.value for r in results)
    requeue = sorted(d for r in results if r.status in REQUEUE_STATUSES for d in r.doc_ids)
    return {
        "batches": {
            r.batch_id: {"status": r.status.value, "http_status": r.http_status, "documents": r.doc_ids}
            for r in results
        },
        "skipped": outcome.skipped,
        "counts": {s.value: counts.get(s.value, 0) for s in BatchStatus},
        "requeue": requeue,
        "index": coverage(outcome.index, results, BatchStatus.OK),
    }
