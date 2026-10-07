from collections import defaultdict
from statistics import median


def reasons_for(by_project, rates):
    reasons = []
    for project, durations in sorted(by_project.items()):
        seconds = median(durations) / 1000
        if seconds < rates[project].min_seconds:
            reasons.append(f"fast:{project}")
    return reasons


def audit_flags(entries, rates):
    """Contributors whose median time per task is below a project's floor."""
    per_contributor = defaultdict(lambda: defaultdict(list))
    for e in entries:
        per_contributor[e.contributor_id][e.project].append(e.duration_ms)
    flags = {}
    for cid in sorted(per_contributor):
        reasons = reasons_for(per_contributor[cid], rates)
        if reasons:
            flags[cid] = reasons
    return flags
