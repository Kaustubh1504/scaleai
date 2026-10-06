"""Build the project throughput report from the Projects API."""

from __future__ import annotations

import statistics
from datetime import datetime, timezone

from report.client import ApiClient

STATUSES = ("pending", "in_progress", "completed", "rejected")


def _parse(timestamp: str) -> datetime:
    return datetime.fromisoformat(timestamp.replace("Z", "+00:00"))


def _iso(epoch: float) -> str:
    return datetime.fromtimestamp(epoch, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rate(done: int, total: int) -> float | None:
    return round(done / total, 4) if total else None


def summarize_project(project: dict, tasks: list[dict]) -> dict:
    completed = [t for t in tasks if t["status"] == "completed"]
    minutes = [(_parse(t["completed_at"]) - _parse(t["created_at"])).total_seconds() / 60
               for t in completed if t.get("completed_at")]
    return {
        "project_id": project["id"],
        "name": project["name"],
        "customer_id": project["customer"]["id"],
        "status": project["status"],
        "tasks_total": len(tasks),
        "tasks_completed": len(completed),
        "completion_rate": _rate(len(completed), len(tasks)),
        "median_minutes_to_complete": round(statistics.median(minutes), 1) if minutes else None,
        "tasks_by_status": {status: sum(t["status"] == status for t in tasks) for status in STATUSES},
    }


def summarize_customers(projects: list[dict], rows: list[dict]) -> list[dict]:
    customers: dict[str, dict] = {}
    for project, row in zip(projects, rows):
        info = project["customer"]
        entry = customers.setdefault(info["id"], {
            "customer_id": info["id"], "customer_name": info["name"], "tier": info.get("tier"),
            "projects": 0, "tasks_total": 0, "tasks_completed": 0,
        })
        entry["projects"] += 1
        entry["tasks_total"] += row["tasks_total"]
        entry["tasks_completed"] += row["tasks_completed"]
    for entry in customers.values():
        entry["completion_rate"] = _rate(entry["tasks_completed"], entry["tasks_total"])
    return [customers[key] for key in sorted(customers)]


def build_report(client: ApiClient) -> dict:
    generated_at = client.clock.time()
    projects = sorted(client.iter_projects(), key=lambda p: p["id"])
    rows = [summarize_project(p, list(client.iter_project_tasks(p["id"]))) for p in projects]
    return {
        "generated_at": _iso(generated_at),
        "projects": rows,
        "customers": summarize_customers(projects, rows),
        "totals": {
            "projects": len(rows),
            "tasks_total": sum(r["tasks_total"] for r in rows),
            "tasks_completed": sum(r["tasks_completed"] for r in rows),
        },
    }
