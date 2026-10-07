import json
from pathlib import Path

from .models import Annotation, Project
from .utils import norm_id, norm_label, norm_task, parse_timestamp, read_rows


def load_projects(path):
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    projects = {}
    for key, item in raw.items():
        pid = norm_id(key)
        projects[pid] = Project(id=pid, min_votes=int(item["min_votes"]), agreement=float(item["agreement"]))
    return projects


def read_batch(path, project):
    annotations = []
    for row in read_rows(path):
        label = norm_label(row.get("label"))
        if not label:
            continue
        annotations.append(Annotation(
            task_id=norm_task(row["task_id"]),
            project=project,
            annotator_id=norm_id(row["annotator_id"]),
            label=label,
            submitted_at=parse_timestamp(row["submitted_at"]),
        ))
    return annotations


def latest_per_annotator(annotations):
    latest = {}
    for ann in annotations:
        key = (ann.task_id, ann.annotator_id, ann.label)
        current = latest.get(key)
        if current is None or ann.submitted_at > current.submitted_at:
            latest[key] = ann
    return list(latest.values())


def load_annotations(batch_dir, projects):
    annotations = []
    for path in sorted(Path(batch_dir).glob("*.csv")):
        project = norm_id(path.stem)
        if project not in projects:
            continue
        annotations.extend(read_batch(path, project))
    return latest_per_annotator(annotations)


def load_teams(path):
    roster = {}
    for row in read_rows(path):
        aid = norm_id(row.get("annotator_id"))
        if aid:
            roster[aid] = norm_id(row.get("team"))
    return roster
