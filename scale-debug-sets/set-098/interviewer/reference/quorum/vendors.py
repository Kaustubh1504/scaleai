import csv
import json

from .models import Vote
from .timeutil import from_epoch, parse_timestamp


def _norm(item_id, annotator_id, label):
    return str(item_id).strip().upper(), str(annotator_id).strip().lower(), str(label or "").strip().lower()


def read_vendor_a(path):
    votes = []
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            item_id, annotator_id, label = _norm(row["item_id"], row["annotator"], row["label"])
            votes.append(Vote(row["vote_id"].strip(), "vendor_a", item_id, annotator_id, label,
                              parse_timestamp(row["submitted_at"])))
    return votes


def read_vendor_b(path):
    votes = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            rec = json.loads(line)
            item_id, annotator_id, label = _norm(rec["task"], rec["worker"], rec.get("answer"))
            votes.append(Vote(str(rec["id"]).strip(), "vendor_b", item_id, annotator_id, label,
                              from_epoch(rec["submitted"])))
    return votes
