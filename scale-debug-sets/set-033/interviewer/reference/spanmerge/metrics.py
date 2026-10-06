from collections import defaultdict


def agreement(spans, accepted):
    """Share of each annotator's spans that ended up accepted."""
    per = defaultdict(set)
    for span in spans:
        per[span.annotator].add(span.key)
    rates = {}
    for annotator in sorted(per):
        keys = per[annotator]
        hits = sum(1 for key in keys if key in accepted)
        rates[annotator] = round(hits / len(keys), 3)
    return rates
