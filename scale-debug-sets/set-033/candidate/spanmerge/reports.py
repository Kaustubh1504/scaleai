from pathlib import Path

from .consensus import vote
from .loader import load_annotators, load_documents, load_spans
from .metrics import agreement

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def entities_by_doc(documents, accepted):
    out = {doc_id: [] for doc_id in sorted(documents)}
    for (doc_id, start, end, label), votes in accepted.items():
        doc = documents[doc_id]
        out[doc_id].append({
            "start": start,
            "end": end,
            "label": label,
            "text": doc.text[start:end + 1],
            "votes": votes,
        })
    for ents in out.values():
        ents.sort(key=lambda e: (e["start"], e["end"]))
    return out


def build_report(data_dir=None):
    data_dir = Path(data_dir or DATA_DIR)
    documents = load_documents(data_dir / "documents.json")
    tools = load_annotators(data_dir / "annotators.json")
    spans, invalid = load_spans(data_dir / "spans.csv", documents, tools)
    accepted = vote(spans)
    return {
        "entities": entities_by_doc(documents, accepted),
        "annotators": {
            ann: {"invalid": invalid.get(ann, 0), "agreement": rate}
            for ann, rate in agreement(spans, accepted).items()
        },
    }
