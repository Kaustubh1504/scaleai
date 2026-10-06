"""Seed manifest.json with the full 100-set plan (domain, length, difficulty).

Safe to re-run: existing entries keep their status, bugs and metadata; only
missing entries are added. This is what makes the library resumable.

    python tools/plan.py
"""
from __future__ import annotations

import sys

from common import load_manifest, save_manifest

TOTAL = 100

ENDPOINT = "endpoint_client"
# Endpoint-client sets land on 4, 12, 20, ... 100 (13 sets); the other
# domains rotate through the remaining slots.
ROTATION = [
    "contributor_assignment",
    "annotation_consensus",
    "task_queue_leases",
    "bbox_qa",
    "review_state_machine",
    "llm_eval_scoring",
    "data_ingestion_dedupe",
    "ner_spans",
    "rate_limit_billing",
    "rlhf_preferences",
    "fraud_detection",
    "load_balancer",
    "sft_formatting",
    "job_scheduler",
    "leaderboard_ranking",
    "robotics_episodes",
    "seat_reservation",
    "cache_ttl",
    "hitl_routing",
    "payouts",
    "dataset_split",
]


def difficulty(n: int) -> str:
    if n <= 20:
        return "easy"
    if n <= 70:
        return "medium"
    return "hard"


# 30 multi-bug-per-test sets (15 MINI, 15 FULL), picked so every domain gets at least
# one; the other 70 are one bug per failing test.
MULTI_SETS = {1, 2, 3, 4, 5, 6, 9, 13, 16, 19, 22, 25, 28, 31, 34, 38, 41, 45, 48, 51,
              56, 59, 63, 66, 71, 74, 77, 80, 86, 90}


def test_format(n: int) -> str:
    return "multi" if n in MULTI_SETS else "one_to_one"


def planned_entries() -> list[dict]:
    entries = []
    rot = 0
    for n in range(1, TOTAL + 1):
        if (n - 4) % 8 == 0:
            domain = ENDPOINT
        else:
            domain = ROTATION[rot % len(ROTATION)]
            rot += 1
        entries.append({
            "id": f"set-{n:03d}",
            "domain": domain,
            "length": "MINI" if n % 2 else "FULL",
            "difficulty": difficulty(n),
            "format": test_format(n),
            "status": "pending",
            "bugs": [],
        })
    return entries


def main() -> int:
    manifest = load_manifest()
    existing = {s["id"]: s for s in manifest.get("sets", [])}
    merged = []
    for planned in planned_entries():
        entry = existing.get(planned["id"], planned)
        entry.setdefault("format", planned["format"])
        merged.append(entry)
    manifest["sets"] = merged
    save_manifest(manifest)
    counts: dict[str, int] = {}
    for s in merged:
        counts[s["domain"]] = counts.get(s["domain"], 0) + 1
    for d, c in sorted(counts.items(), key=lambda kv: -kv[1]):
        print(f"{d:24s} {c}")
    for fmt in ("one_to_one", "multi"):
        rows = [s for s in merged if s["format"] == fmt]
        print(f"{fmt}: {len(rows)} ({sum(s['length'] == 'MINI' for s in rows)} MINI)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
