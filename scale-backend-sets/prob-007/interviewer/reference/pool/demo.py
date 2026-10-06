"""Demo: run data/jobs.jsonl through a pool of three local workers.

    python -m pool.demo [path/to/jobs.jsonl]

Works once Part 1 is done; shows more as you finish Parts 2 and 3.

Each line of the jobs file is a JSON object: {"id": non-empty str, "payload":
any (optional, default {"id": <id>})}. Lines that do not match are skipped
with a warning. What the demo workers do with a payload:

    "fail": true        always raises            -> TaskFailedError on every attempt
    "fail_times": n     raises on its first n attempts, then succeeds
    "crash": true       the worker dies mid-job  -> WorkerUnreachableError (a poison job)

A "supervisor" restarts dead workers a few rounds after they die, so you can
watch them rejoin through their heartbeats.
"""

from __future__ import annotations

import json
import logging
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from mock_services.clock import RealClock
from mock_services.workers import CrashingWorker, WorkerFleet, default_handler
from pool.coordinator import Pool

DEFAULT_JOBS = Path(__file__).resolve().parent.parent / "data" / "jobs.jsonl"
ROUND_S = 0.02  # real seconds between rounds
RESTART_AFTER_ROUNDS = 3

log = logging.getLogger("pool.demo")


def _parse_job(line: str) -> tuple[str, Any]:
    row = json.loads(line)  # json.JSONDecodeError is a ValueError
    if not isinstance(row, dict):
        raise ValueError("line is not a JSON object")
    job_id = row.get("id")
    if not isinstance(job_id, str) or not job_id:
        raise ValueError("id must be a non-empty string")
    return job_id, row.get("payload", {"id": job_id})


def load_jobs(path: Path) -> list[tuple[str, Any]]:
    jobs = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            jobs.append(_parse_job(line))
        except ValueError as exc:
            log.warning("%s:%d skipped: %s", path.name, lineno, exc)
    return jobs


def make_handler():
    """The demo workers' job logic. Attempts are counted per job id across all workers."""
    seen: Counter[str] = Counter()

    def handler(worker_id: str, payload: Any) -> Any:
        if isinstance(payload, dict):
            key = str(payload.get("id"))
            seen[key] += 1
            if payload.get("fail"):
                raise ValueError("unsupported input")
            if seen[key] <= payload.get("fail_times", 0):
                raise RuntimeError(f"transient error (attempt {seen[key]})")
        return default_handler(worker_id, payload)

    return handler


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    path = Path(argv[0]) if argv else DEFAULT_JOBS
    clock = RealClock()
    handler = make_handler()
    fleet = WorkerFleet([CrashingWorker(f"w{i}", latency_s=0.005, clock=clock, handler=handler) for i in (1, 2, 3)],
                        clock=clock)
    pool = Pool(list(fleet), clock, concurrency_per_worker=2, job_timeout_s=0.5, backoff_base_s=0.05)

    for job_id, payload in load_jobs(path):
        try:
            if not pool.submit(job_id, payload):
                log.info("duplicate of %s ignored", job_id)
        except ValueError as exc:
            log.warning("not queued: %s", exc)

    dead_for: Counter[str] = Counter()
    for _ in range(40):
        if not pool.pending():
            break
        for worker in fleet:  # the supervisor
            dead_for[worker.worker_id] = dead_for[worker.worker_id] + 1 if worker.heartbeat() is None else 0
            if dead_for[worker.worker_id] > RESTART_AFTER_ROUNDS:
                log.info("supervisor: restarting %s", worker.worker_id)
                worker.revive()
        fleet.emit_heartbeats(pool.on_heartbeat)
        pool.tick()
        clock.sleep(ROUND_S)

    left = pool.drain()
    for job_id, result in pool.results.items():
        print(f"{job_id:<14} -> {result['worker_id']} (attempts={pool.job(job_id)['attempts']})")
    for letter in pool.dead_letters:
        print(f"{letter['job_id']:<14} !! dead-lettered ({letter['reason']}) after "
              f"{[h['worker_id'] for h in letter['history']]}")
    print("left unfinished:", left)
    print("status:", pool.status())
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
