from collections import Counter
from pathlib import Path

from .loader import load_aliases, load_documents, read_annotations, read_gold
from .scoring import confusion_counts, score_annotators
from .spans import normalize_all

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def export_spans(spans, docs, gold_docs):
    out = {}
    for span in sorted(spans, key=lambda s: (s.doc_id, s.start, s.end, s.annotator)):
        if span.doc_id in gold_docs:
            continue
        text = docs[span.doc_id][span.start:span.end]
        out.setdefault(span.doc_id, []).append([span.start, span.end, span.label, span.annotator, text])
    return out


def rank_confusions(counts):
    ranked = counts.most_common()
    return [[gold_label, label, n] for (gold_label, label), n in ranked]


def build_report(data_dir=None):
    data_dir = Path(data_dir or DATA_DIR)
    docs = load_documents(data_dir / "documents.json")
    aliases = load_aliases(data_dir / "labels.json")
    gold = read_gold(data_dir / "gold.csv")
    spans, rejected = normalize_all(read_annotations(data_dir / "annotations.csv"), docs, aliases)
    gold_docs = {g[0] for g in gold}
    return {
        "export": export_spans(spans, docs, gold_docs),
        "rejected": dict(sorted(rejected.items())),
        "accepted": dict(sorted(Counter(s.annotator for s in spans).items())),
        "scores": score_annotators(spans, gold),
        "confusions": rank_confusions(confusion_counts(spans, gold)),
        "gold_labels": dict(sorted(Counter(g[3] for g in gold).items())),
    }
