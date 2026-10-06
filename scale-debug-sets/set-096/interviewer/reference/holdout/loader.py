import csv
import json

from .models import Sample, Source
from .textnorm import clean, norm_doc, norm_label, norm_sample_id, parse_date


def load_sources(path):
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    sources = {}
    for item in raw:
        doc = norm_doc(item["doc"])
        sources[doc] = Source(doc=doc, license=clean(item.get("license")).lower())
    return sources


def _quality(value):
    text = clean(value)
    return float(text) if text else None


def load_samples(path):
    samples = []
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            samples.append(Sample(
                sample_id=norm_sample_id(row["sample_id"]),
                doc=norm_doc(row["doc_id"]),
                label=norm_label(row["label"]),
                text=clean(row["text"]),
                quality=_quality(row["quality"]),
                created=parse_date(row["created"]),
            ))
    return samples
