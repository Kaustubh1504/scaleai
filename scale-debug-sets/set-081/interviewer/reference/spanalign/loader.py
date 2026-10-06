import csv
import json


def clean(value):
    return (value or "").strip()


def norm_doc(value):
    return clean(value).upper()


def norm_annotator(value):
    return clean(value).lower()


def load_documents(path):
    with open(path, encoding="utf-8") as fh:
        rows = json.load(fh)
    return {norm_doc(row["doc_id"]): row["text"] for row in rows}


def load_aliases(path):
    """Map every lower-cased alias (and each canonical label itself) to its canonical label."""
    with open(path, encoding="utf-8") as fh:
        rows = json.load(fh)
    aliases = {}
    for row in rows:
        label = clean(row["label"]).upper()
        aliases[label.lower()] = label
        alias = clean(row["alias"]).lower()
        if alias:
            aliases[alias] = label
    return aliases


def read_annotations(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return [
            {
                "doc_id": norm_doc(row["doc_id"]),
                "annotator": norm_annotator(row["annotator"]),
                "start": clean(row["start"]),
                "end": clean(row["end"]),
                "label": clean(row["label"]),
            }
            for row in csv.DictReader(fh)
        ]


def read_gold(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return [
            (norm_doc(row["doc_id"]), int(row["start"]), int(row["end"]), clean(row["label"]).upper())
            for row in csv.DictReader(fh)
        ]
