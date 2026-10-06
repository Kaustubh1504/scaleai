import statistics
from collections import Counter
from pathlib import Path

from .runner import run_batch

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
STATUSES = ("ok", "parse_error", "http_error")


def summarize(results, usage):
    ok = [r for r in results if r.status == "ok"]
    counts = Counter(r.status for r in results)
    latencies = [u["latency_ms"] for u in usage]
    return {
        "counts": {s: counts.get(s, 0) for s in STATUSES},
        "mean_score": round(statistics.mean(r.score for r in ok), 2) if ok else None,
        "pass_rate": round(sum(1 for r in ok if r.passed) / len(ok), 3) if ok else None,
        "total_tokens": sum(u["total_tokens"] for u in usage),
        "p50_latency_s": round(statistics.median(latencies) / 1000, 3) if latencies else None,
    }


def build_report(base_url, api_key, data_dir=None, sleep=None):
    results, usage = run_batch(base_url, data_dir or DATA_DIR, api_key, sleep=sleep)
    return {
        "results": {
            r.request_id: {"status": r.status, "http_status": r.http_status, "score": r.score, "passed": r.passed}
            for r in results
        },
        "order": [r.request_id for r in results],
        "summary": summarize(results, usage),
    }
