"""Per-annotator earnings for a pay period (PART1.md / PART2.md).

All money is integer cents. Fetching happens in ``compute_earnings``; everything
else is pure functions over records, so the rules are testable without the API.
"""

from __future__ import annotations

from datetime import datetime, timezone

from earnings import normalize
from earnings.client import EarningsClient

COUNTS = ("approved", "rejected", "pending")


def iso(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def period_label(period_start: datetime, period_end: datetime) -> str:
    """'2024-04-01T00:00:00Z/2024-04-15T00:00:00Z' (both ends in UTC)."""
    return f"{iso(period_start)}/{iso(period_end)}"


def latest_verdicts(reviews: list[dict]) -> dict[str, str]:
    """submission_id -> verdict of its most recent review (ties: highest review id)."""
    best: dict[str, tuple] = {}
    for review in reviews:
        key = (normalize.parse_ts(review["created_at"]), review["id"])
        current = best.get(review["submission_id"])
        if current is None or key > current[0]:
            best[review["submission_id"]] = (key, normalize.verdict(review["verdict"]))
    return {submission_id: verdict for submission_id, (_, verdict) in best.items()}


def gold_bonus_cents(task: dict, submission: dict, reward: int) -> int:
    """Mid-part change: +50% (rounded down) for a correct answer on a gold task."""
    gold = task.get("gold_label")
    if not normalize.flag(task.get("is_gold", False)) or gold is None:
        return 0
    answer = (submission.get("answer") or {}).get("label")
    return reward // 2 if normalize.label(answer) == normalize.label(gold) else 0


def new_row(annotator_id: str, annotator: dict | None) -> dict:
    if annotator is None:
        raise normalize.DataError(f"submission by unknown annotator {annotator_id}")
    return {"annotator_id": annotator_id, "handle": annotator.get("handle"), **{c: 0 for c in COUNTS},
            "earnings_cents": 0, "gold_bonus_cents": 0, "on_hold": not normalize.flag(annotator["is_active"])}


def summarize(annotators: dict[str, dict], tasks: dict[str, dict], submissions: list[dict],
              verdicts: dict[str, str], period_start: datetime, period_end: datetime) -> dict:
    rows: dict[str, dict] = {}
    unknown_reward: set[str] = set()
    for sub in submissions:
        if not period_start <= normalize.parse_ts(sub["submitted_at"]) < period_end:
            continue
        annotator_id = sub["annotator_id"]
        if annotator_id not in rows:
            rows[annotator_id] = new_row(annotator_id, annotators.get(annotator_id))
        row = rows[annotator_id]
        verdict = verdicts.get(sub["id"], "pending")
        row[verdict] += 1
        if verdict != "approved":
            continue
        task = tasks.get(sub["task_id"])
        if task is None:
            raise normalize.DataError(f"submission {sub['id']} references unknown task {sub['task_id']}")
        reward = normalize.reward_cents(task)
        if reward is None:
            unknown_reward.add(task["id"])
            continue
        bonus = gold_bonus_cents(task, sub, reward)
        row["earnings_cents"] += reward + bonus
        row["gold_bonus_cents"] += bonus

    ordered = [rows[key] for key in sorted(rows)]
    totals = {"annotators": len(ordered), **{c: sum(r[c] for r in ordered) for c in COUNTS},
              "earnings_cents": sum(r["earnings_cents"] for r in ordered),
              "payable_cents": sum(r["earnings_cents"] for r in ordered if not r["on_hold"])}
    return {"period": period_label(period_start, period_end), "annotators": ordered,
            "unknown_reward_task_ids": sorted(unknown_reward), "totals": totals}


def compute_earnings(client: EarningsClient, period_start: datetime, period_end: datetime) -> dict:
    if period_start.tzinfo is None or period_end.tzinfo is None or period_start >= period_end:
        raise ValueError("period_start and period_end must be timezone-aware with start < end")
    annotators = {a["id"]: a for a in client.list_all("annotators")}
    tasks = {t["id"]: t for t in client.list_all("tasks")}
    verdicts = latest_verdicts(client.list_all("reviews"))
    return summarize(annotators, tasks, client.list_all("submissions"), verdicts, period_start, period_end)
