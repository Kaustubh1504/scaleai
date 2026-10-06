from collections import Counter, defaultdict

MIN_VOTES = 2


def majority_label(labels):
    counts = Counter(labels)
    return min(counts, key=lambda label: (-counts[label], label))


def build_entities(kept, docs):
    by_doc = defaultdict(list)
    for (_, doc_id), spans in kept.items():
        by_doc[doc_id].extend(spans)

    entities = {}
    for doc_id in sorted(docs):
        spans = by_doc.get(doc_id)
        if not spans:
            continue
        votes = defaultdict(dict)
        for span in spans:
            votes[(span.start, span.end)][span.annotator] = span.label
        found = []
        for (start, end), labels in sorted(votes.items()):
            if len(labels) >= MIN_VOTES:
                found.append({
                    "text": docs[doc_id][start:end],
                    "label": majority_label(labels.values()),
                    "start": start,
                    "end": end,
                    "votes": len(labels),
                })
        if found:
            entities[doc_id] = found
    return entities
