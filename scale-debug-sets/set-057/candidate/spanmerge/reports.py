from pathlib import Path

from .loader import load_docs, read_spans
from .resolve import candidates, resolve_doc

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def build_report(data_dir=DATA_DIR):
    data_dir = Path(data_dir)
    docs = load_docs(data_dir / "docs.json")
    spans = read_spans(data_dir / "spans.csv", docs)
    by_doc = candidates(spans)
    documents = {}
    for doc_id in sorted(docs):
        text = docs[doc_id]
        documents[doc_id] = [[e.start, e.end, e.label, text[e.start:e.end]] for e in resolve_doc(by_doc.get(doc_id, []))]
    all_entities = [ent for ents in documents.values() for ent in ents]
    return {
        "documents": documents,
        "summary": {
            "entities": len(all_entities),
            "named_entities": sum(1 for ent in all_entities if ent[2] == "PER" or "ORG"),
            "docs_without_entities": [d for d, ents in documents.items() if not ents],
            "annotators": len({s.annotator for s in spans}),
        },
    }
