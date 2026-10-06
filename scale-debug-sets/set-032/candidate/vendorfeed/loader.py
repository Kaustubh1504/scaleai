import csv
import json

from .models import Record
from .utils import clean, norm_email, norm_label, norm_task, parse_duration, parse_timestamp, split_tags


def read_rows(path):
    if path.suffix == ".json":
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def to_record(raw, vendor, row, settings):
    label = norm_label(raw.get("label"))
    return Record(
        vendor=vendor,
        row=row,
        priority=int(settings["priority"]),
        task_id=norm_task(raw.get("task_id")),
        email=norm_email(raw.get("email")),
        label=settings["label_map"].get(label, label),
        batch=clean(raw.get("batch")).lower() or "unbatched",
        submitted=parse_timestamp(raw.get("submitted")),
        duration_s=parse_duration(raw.get("duration_s")),
        tags=split_tags(raw.get("tags")),
    )


def load_vendor(data_dir, vendor, settings):
    rows = read_rows(data_dir / settings["file"])
    return [to_record(raw, vendor, n, settings) for n, raw in enumerate(rows, start=1)]
