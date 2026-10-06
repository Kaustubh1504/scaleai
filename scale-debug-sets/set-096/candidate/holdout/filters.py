def drop_blocked(samples, sources, blocked_licenses, dropped):
    """Remove samples whose source document is unknown or carries a blocked license."""
    for sample in samples:
        source = sources.get(sample.doc)
        if source is None or source.license in blocked_licenses:
            dropped[sample.sample_id] = "blocked_source"
            samples.remove(sample)
    return samples


def drop_incomplete(samples, dropped):
    kept = []
    for sample in samples:
        if not sample.text or not sample.label:
            dropped[sample.sample_id] = "incomplete"
        else:
            kept.append(sample)
    return kept


def drop_low_quality(samples, min_quality, dropped):
    kept = []
    for sample in samples:
        if sample.quality is not None and sample.quality < min_quality:
            dropped[sample.sample_id] = "low_quality"
        else:
            kept.append(sample)
    return kept


def apply_filters(samples, sources, config):
    dropped = {}
    rows = drop_blocked(list(samples), sources, config.blocked_licenses, dropped)
    rows = drop_incomplete(rows, dropped)
    rows = drop_low_quality(rows, config.min_quality, dropped)
    return rows, dropped
