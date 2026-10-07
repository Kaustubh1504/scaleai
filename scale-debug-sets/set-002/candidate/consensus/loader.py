import csv
import json

from .models import Annotation, Annotator
from .utils import clean, norm_annotator, norm_label, norm_task, parse_bool, parse_timestamp


def load_annotators(path):
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    registry = {}
    for item in raw:
        aid = norm_annotator(item["id"])
        # print(item.get("active", True), parse_bool(item.get("active", True)))
        registry[aid] = Annotator(id=aid, name=clean(item.get("name")), active=parse_bool(item.get("active", True)))
    return registry


def load_tasks(path):
    """Return (task ids in file order, {task_id: gold_label} for gold tasks)."""
    task_ids, gold = [], {}
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            tid = norm_task(row["task_id"])
            task_ids.append(tid)
            label = norm_label(row["gold_label"])
            if label:
                gold[tid] = label
    return task_ids, gold


def read_annotations(path):
    annotations = []
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            label = norm_label(row["label"])
            if not label:
                continue
            annotations.append(Annotation(
                task_id=norm_task(row["task_id"]),
                annotator_id=norm_annotator(row["annotator_id"]),
                label=label,
                submitted_at=parse_timestamp(row["submitted_at"]),
            ))
    return annotations


# VERIFIED
def latest_submissions(annotations):
    latest = {}
    for ann in annotations:
        key = (ann.task_id, ann.annotator_id)
        current = latest.get(key)
        if current is None or ann.submitted_at >= current.submitted_at:
            latest[key] = ann
    return list(latest.values())


def load_annotations(path, registry):
    rows = [a for a in read_annotations(path)
            if a.annotator_id in registry and registry[a.annotator_id].active]
    return latest_submissions(rows)
