from collections import Counter, defaultdict
from pathlib import Path

from .consensus import build_entities
from .loader import load_docs, load_spans
from .spans import clean_spans

DATA = Path(__file__).resolve().parent.parent / "data"


def build_report(data_dir=DATA):
    data_dir = Path(data_dir)
    docs = load_docs(data_dir / "docs.json")
    kept, misaligned = clean_spans(load_spans(data_dir / "annotations.csv"), docs)
    entities = build_entities(kept, docs)

    per_annotator = defaultdict(dict)
    for (annotator, doc_id), spans in kept.items():
        per_annotator[annotator][doc_id] = [[s.start, s.end, s.label] for s in spans]
    return {
        "kept": dict(per_annotator),
        "misaligned": sorted((s.doc_id, s.annotator, s.quote) for s in misaligned),
        "entities": entities,
        "label_counts": dict(sorted(Counter(e["label"] for ents in entities.values() for e in ents).items())),
    }
