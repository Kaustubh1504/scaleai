"""Per-annotator earnings for a pay period.

Contributors are paid the task's reward for each submission they made in the
period. Written for the Q1 payout run.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone

from earnings.client import EarningsClient


def parse_ts(value: str) -> datetime:
    """'2024-04-02T10:15:00Z' -> aware datetime."""
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def iso(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def period_label(period_start: datetime, period_end: datetime) -> str:
    """'2024-04-01T00:00:00Z/2024-04-15T00:00:00Z' (both ends in UTC)."""
    return f"{iso(period_start)}/{iso(period_end)}"


def in_period(moment: datetime, period_start: datetime, period_end: datetime) -> bool:
    return period_start <= moment <= period_end


def summarize(submissions: list[dict], tasks_by_id: dict[str, dict]) -> dict[str, dict]:
    """annotator_id -> {"submissions": n, "earnings_usd": dollars}."""
    out: dict[str, dict] = defaultdict(lambda: {"submissions": 0, "earnings_usd": 0.0})
    for sub in submissions:
        task = tasks_by_id.get(sub["task_id"])
        if task is None:
            continue  # task was deleted
        row = out[sub["annotator_id"]]
        row["submissions"] += 1
        row["earnings_usd"] += int(task["reward_cents"]) / 100
    return out


def compute_earnings(client: EarningsClient, period_start: datetime, period_end: datetime) -> dict:
    tasks = {t["id"]: t for t in client.list_all("tasks")}
    submissions = [s for s in client.list_all("submissions")
                   if in_period(parse_ts(s["submitted_at"]), period_start, period_end)]
    per_annotator = summarize(submissions, tasks)

    rows = []
    for annotator_id in sorted(per_annotator):
        usd = per_annotator[annotator_id]["earnings_usd"]
        rows.append({
            "annotator_id": annotator_id,
            "submissions": per_annotator[annotator_id]["submissions"],
            "earnings_usd": round(usd, 2),
            "earnings_cents": int(usd * 100),
        })
    return {
        "period": period_label(period_start, period_end),
        "annotators": rows,
        "totals": {"annotators": len(rows), "earnings_cents": sum(r["earnings_cents"] for r in rows)},
    }
