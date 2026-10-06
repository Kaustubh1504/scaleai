"""A deterministic, Scale-flavoured dataset of related resources.

    projects ──< tasks ──< submissions ──< reviews
                              └── annotator_id ──> annotators

Each resource uses a different pagination style and envelope, like a real API
that grew over several years:

| resource | pagination | envelope | nested via |
|---|---|---|---|
| projects | page (page, per_page) | results / page / per_page / total / total_pages | |
| annotators | offset (offset, limit) | items / offset / limit / total | |
| tasks | cursor (cursor, limit) | data / next_cursor | /v1/projects/{id}/tasks |
| submissions | cursor | data / next_cursor | /v1/tasks/{id}/submissions |
| reviews | page | results / ... | /v1/submissions/{id}/reviews |
| results | page; writable sink | results / ... | |

Field mess (see ``messy.py``) is applied per record; ``api.canonical(name)``
returns the clean values.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

from .config import FieldMess, ResourceConfig

EPOCH = datetime(2024, 3, 1, tzinfo=timezone.utc)
LABELS = {
    "image_bbox": ["car", "pedestrian", "cyclist", "sign"],
    "text_classification": ["positive", "negative", "neutral"],
    "lidar_cuboid": ["vehicle", "person", "animal"],
}
CUSTOMERS = [("cus_01", "Acme Robotics", "enterprise"), ("cus_02", "Globex AI", "growth"),
             ("cus_03", "Initech Vision", "startup"), ("cus_04", "Umbrella Labs", "enterprise")]
COUNTRIES = ["US", "PH", "KE", "IN", "BR", "PL", "VN"]


def _iso(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def scale_records(seed: int = 0, *, projects: int = 6, annotators: int = 30, tasks: int = 240,
                  submissions_per_task: tuple[int, int] = (0, 3), review_rate: float = 0.6) -> dict[str, list[dict]]:
    rng = random.Random(f"scale-dataset|{seed}")
    out: dict[str, list[dict]] = {k: [] for k in ("projects", "annotators", "tasks", "submissions", "reviews")}

    for i in range(1, projects + 1):
        cus = CUSTOMERS[(i - 1) % len(CUSTOMERS)]
        task_type = rng.choice(list(LABELS))
        created = EPOCH + timedelta(days=rng.randint(0, 20), minutes=rng.randint(0, 1440))
        out["projects"].append({
            "id": f"prj_{i:02d}", "name": f"{cus[1].split()[0]} {task_type.replace('_', ' ')} {i}",
            "customer": {"id": cus[0], "name": cus[1], "tier": cus[2]},
            "status": rng.choices(["active", "paused", "archived"], [6, 2, 1])[0],
            "task_type": task_type,
            "settings": {"redundancy": rng.choice([1, 2, 3]), "gold_ratio": rng.choice([0.0, 0.05, 0.1]),
                         "labels": LABELS[task_type]},
            "created_at": _iso(created), "updated_at": _iso(created + timedelta(days=rng.randint(0, 30))),
        })

    for i in range(1, annotators + 1):
        joined = EPOCH - timedelta(days=rng.randint(10, 700))
        out["annotators"].append({
            "id": f"ann_{i:03d}", "handle": f"annotator{i:03d}", "country": rng.choice(COUNTRIES),
            "level": rng.randint(1, 5), "hourly_rate_cents": rng.choice([450, 600, 750, 900, 1200]),
            "skills": sorted(rng.sample(list(LABELS), rng.randint(1, 3))),
            "is_active": rng.random() > 0.15,
            "joined_at": _iso(joined), "updated_at": _iso(joined + timedelta(days=rng.randint(0, 9))),
        })

    sub_n = rev_n = 0
    for i in range(1, tasks + 1):
        project = rng.choice(out["projects"])
        labels = project["settings"]["labels"]
        created = EPOCH + timedelta(days=rng.randint(21, 50), seconds=rng.randint(0, 86_400))
        status = rng.choices(["pending", "in_progress", "completed", "rejected"], [3, 2, 6, 1])[0]
        is_gold = rng.random() < 0.12
        payload: dict = ({"text": f"Sample sentence {i} for review."} if project["task_type"] == "text_classification"
                         else {"image_url": f"https://cdn.example.com/img/{i:05d}.jpg",
                               "dimensions": None if rng.random() < 0.1 else
                               {"width": rng.choice([640, 1280, 1920]), "height": rng.choice([480, 720, 1080])}})
        completed = created + timedelta(minutes=rng.randint(5, 600)) if status == "completed" else None
        task = {
            "id": f"tsk_{i:04d}", "project_id": project["id"], "status": status, "priority": rng.randint(1, 5),
            "is_gold": is_gold, "gold_label": rng.choice(labels) if is_gold else None, "payload": payload,
            "tags": sorted(rng.sample(["night", "rain", "urban", "highway", "occluded", "blurry"], rng.randint(0, 3))),
            "reward_cents": rng.choice([5, 8, 12, 20, 35]),
            "created_at": _iso(created), "completed_at": _iso(completed) if completed else None,
            "updated_at": _iso(completed or created),
        }
        out["tasks"].append(task)
        if status == "pending":
            continue
        for annotator in rng.sample(out["annotators"], rng.randint(*submissions_per_task)):
            sub_n += 1
            submitted = created + timedelta(minutes=rng.randint(1, 300))
            label = task["gold_label"] if is_gold and rng.random() < 0.7 else rng.choice(labels)
            boxes = [] if project["task_type"] == "text_classification" else [
                {"x": rng.randint(0, 500), "y": rng.randint(0, 400), "w": rng.randint(10, 200),
                 "h": rng.randint(10, 200), "label": rng.choice(labels)} for _ in range(rng.randint(0, 3))]
            submission = {
                "id": f"sub_{sub_n:05d}", "task_id": task["id"], "annotator_id": annotator["id"],
                "submitted_at": _iso(submitted), "duration_s": round(rng.uniform(20, 900), 1),
                "answer": {"label": label, "confidence": round(rng.uniform(0.4, 1.0), 2), "boxes": boxes},
                "updated_at": _iso(submitted),
            }
            out["submissions"].append(submission)
            if rng.random() < review_rate:
                rev_n += 1
                reviewer = rng.choice([a for a in out["annotators"] if a["id"] != annotator["id"]])
                reviewed = submitted + timedelta(minutes=rng.randint(10, 2000))
                verdict = rng.choices(["approved", "rejected"], [4, 1])[0]
                out["reviews"].append({
                    "id": f"rev_{rev_n:05d}", "submission_id": submission["id"], "reviewer_id": reviewer["id"],
                    "verdict": verdict, "score": rng.randint(1, 5) if rng.random() > 0.1 else None,
                    "comment": None if rng.random() < 0.6 else rng.choice(["Missed a box.", "Good work.",
                                                                          "Wrong label.", "Loose boxes."]),
                    "created_at": _iso(reviewed), "updated_at": _iso(reviewed),
                })
    return out


def scale_resources(seed: int = 0, *, messy: bool = True, **sizes) -> list[ResourceConfig]:
    data = scale_records(seed, **sizes)
    mess = (lambda rules: rules) if messy else (lambda rules: [])
    return [
        ResourceConfig("projects", data["projects"], pagination="page", default_page_size=5, max_page_size=50,
                       filters=("status", "customer.id", "task_type"),
                       mess=mess([FieldMess("customer.tier", ["missing", "upper"], 0.25),
                                  FieldMess("settings.gold_ratio", ["str", "null"], 0.2),
                                  FieldMess("created_at", ["epoch", "iso_offset"], 0.3)])),
        ResourceConfig("annotators", data["annotators"], pagination="offset", default_page_size=10, max_page_size=50,
                       filters=("country", "level", "is_active"),
                       mess=mess([FieldMess("is_active", ["bool_str", "bool_int"], 0.3),
                                  FieldMess("hourly_rate_cents", ["str", "float"], 0.2),
                                  FieldMess("skills", ["csv"], 0.25),
                                  FieldMess("country", ["lower", "null"], 0.1)])),
        ResourceConfig("tasks", data["tasks"], pagination="cursor", default_page_size=25, max_page_size=100,
                       filters=("project_id", "status", "is_gold"), parent=("projects", "project_id"),
                       mess=mess([FieldMess("reward_cents", ["str", "null"], 0.12),
                                  FieldMess("priority", ["str"], 0.15),
                                  FieldMess("tags", ["csv", "missing"], 0.2),
                                  FieldMess("created_at", ["epoch", "epoch_ms", "iso_naive"], 0.2),
                                  FieldMess("payload.dimensions", ["missing"], 0.1),
                                  FieldMess("status", ["upper", "padded"], 0.1)])),
        ResourceConfig("submissions", data["submissions"], pagination="cursor", default_page_size=50,
                       max_page_size=100, filters=("task_id", "annotator_id"), parent=("tasks", "task_id"),
                       mess=mess([FieldMess("answer.confidence", ["str", "null"], 0.15),
                                  FieldMess("answer.label", ["upper", "padded"], 0.15),
                                  FieldMess("answer.boxes", ["missing", "null"], 0.1),
                                  FieldMess("duration_s", ["str"], 0.15),
                                  FieldMess("submitted_at", ["epoch", "iso_offset"], 0.2)])),
        ResourceConfig("reviews", data["reviews"], pagination="page", default_page_size=20, max_page_size=50,
                       filters=("reviewer_id", "verdict", "submission_id"), parent=("submissions", "submission_id"),
                       mess=mess([FieldMess("verdict", ["upper", "padded"], 0.2),
                                  FieldMess("score", ["str"], 0.15),
                                  FieldMess("comment", ["missing", "empty_str"], 0.3)])),
        ResourceConfig("results", [], pagination="page", writable=True, updated_field=None),
    ]
