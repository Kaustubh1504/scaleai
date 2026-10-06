import csv
import json
from dataclasses import dataclass


@dataclass(frozen=True)
class Span:
    doc_id: str
    annotator: str
    start: int
    end: int  # exclusive
    label: str
    quote: str

    @property
    def length(self):
        return self.end - self.start


def load_docs(path):
    with open(path, encoding="utf-8") as fh:
        return {item["doc_id"].strip().lower(): item["text"] for item in json.load(fh)}


def load_spans(path):
    spans = []
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            start, end = int(row["start"]), int(row["end"])
            spans.append(Span(
                doc_id=row["doc_id"].strip().lower(),
                annotator=row["annotator"].strip().lower(),
                start=start,
                end=end,
                label=row["label"].strip().upper(),
                quote=row["quote"].strip(),
            ))
    return spans
