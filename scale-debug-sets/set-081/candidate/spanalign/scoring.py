from collections import Counter, defaultdict


def _key(span):
    return (span.doc_id, span.start, span.end, span.label)


def _ratio(num, den):
    return num / den if den else 0.0


def score_annotators(spans, gold):
    gold_docs = {g[0] for g in gold}
    gold_set = set(gold)
    scored = [s for s in spans if s.doc_id in gold_docs]

    predicted, docs_seen = defaultdict(set), defaultdict(set)
    for span in spans:
        predicted[span.annotator].add(_key(span))
        docs_seen[span.annotator].add(span.doc_id)

    table = {}
    for annotator in sorted(predicted):
        relevant = {g for g in gold_set if g[0] in docs_seen[annotator]}
        tp = len(predicted[annotator] & relevant)
        fp = len(predicted[annotator]) - tp
        fn = len(relevant) - tp
        precision = _ratio(tp, tp + fp)
        recall = _ratio(tp, tp + fn)
        f1 = _ratio(2 * precision * recall, precision + recall)
        table[annotator] = {
            "tp": tp, "fp": fp, "fn": fn,
            "precision": round(precision, 3), "recall": round(recall, 3), "f1": round(f1, 3),
        }
    return table


def confusion_counts(spans, gold):
    """(gold label, annotator label) pairs for spans whose offsets match gold but whose label does not."""
    gold_labels = {(g[0], g[1], g[2]): g[3] for g in gold}
    counts = Counter()
    for span in spans:
        expected = gold_labels.get((span.doc_id, span.start, span.end))
        if expected is not None and expected != span.label:
            counts[(expected, span.label)] += 1
    return counts
