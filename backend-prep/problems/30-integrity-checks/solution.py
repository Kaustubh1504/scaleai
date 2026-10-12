"""30. Integrity checks across entities: reference solution."""

from collections import defaultdict
from datetime import datetime
from typing import NamedTuple

ANNOTATOR_STATUSES = {"active", "suspended", "offboarded"}
TASK_STATUSES = {"open", "in_progress", "completed", "cancelled"}
SUBMISSION_STATUSES = {"pending", "accepted", "rejected"}


class Violation(NamedTuple):
    entity: str
    id: str
    rule: str
    detail: str


def _instant(value) -> datetime | None:
    try:
        dt = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None
    return dt if dt.tzinfo is not None else None  # naive: we can't know which instant it is


def check(dataset: dict) -> list[Violation]:
    out = []
    first = {}
    for entity in ("annotator", "task", "submission"):
        copies = defaultdict(list)
        for rec in dataset[entity + "s"]:
            copies[rec["id"]].append(rec)
        for rid, recs in copies.items():
            if len(recs) > 1:
                rule = "duplicate" if all(r == recs[0] for r in recs) else "conflicting_duplicate"
                out.append(Violation(entity, rid, rule, f"{len(recs)} copies"))
        first[entity] = {rid: recs[0] for rid, recs in copies.items()}
    annotators, tasks = first["annotator"], first["task"]

    for a in annotators.values():
        if a["status"] not in ANNOTATOR_STATUSES:
            out.append(Violation("annotator", a["id"], "bad_status", repr(a["status"])))

    for t in tasks.values():
        tid, created, completed = t["id"], _instant(t["created_at"]), _instant(t["completed_at"])
        if t["status"] not in TASK_STATUSES:
            out.append(Violation("task", tid, "bad_status", repr(t["status"])))
        if type(t["reward_cents"]) is not int or t["reward_cents"] < 0:
            out.append(Violation("task", tid, "bad_reward", repr(t["reward_cents"])))
        if created is None:
            out.append(Violation("task", tid, "bad_timestamp", repr(t["created_at"])))
        if t["completed_at"] is not None and completed is None:
            out.append(Violation("task", tid, "bad_timestamp", repr(t["completed_at"])))
        if t["status"] == "completed" and t["completed_at"] is None:
            out.append(Violation("task", tid, "missing_completed_at", "completed_at is null"))
        if created and completed and completed < created:
            out.append(Violation("task", tid, "completed_before_created", t["completed_at"]))

    for s in first["submission"].values():
        sid, conf, submitted = s["id"], s["confidence"], _instant(s["submitted_at"])
        task, annotator = tasks.get(s["task_id"]), annotators.get(s["annotator_id"])
        if s["status"] not in SUBMISSION_STATUSES:
            out.append(Violation("submission", sid, "bad_status", repr(s["status"])))
        if type(conf) not in (int, float) or not 0 <= conf <= 1:  # NaN fails the range check
            out.append(Violation("submission", sid, "bad_confidence", repr(conf)))
        if submitted is None:
            out.append(Violation("submission", sid, "bad_timestamp", repr(s["submitted_at"])))
        if task is None:
            out.append(Violation("submission", sid, "unknown_task", repr(s["task_id"])))
        if annotator is None:
            out.append(Violation("submission", sid, "unknown_annotator", repr(s["annotator_id"])))
        if task and submitted and (created := _instant(task["created_at"])) and submitted < created:
            out.append(Violation("submission", sid, "submitted_before_task_created", task["id"]))
        if task and annotator and task["project_id"] not in annotator["projects"]:
            out.append(Violation("submission", sid, "annotator_not_on_project", task["project_id"]))

    return sorted(out)


if __name__ == "__main__":
    from problem_api import load_dataset

    for v in check(load_dataset()):
        print(*v)
