from collections import Counter, defaultdict

from .models import TaskResult


# VERIFIED
def decide(counts, project):
    ranked = counts.most_common()
    top_label, top = ranked[0]
    if len(ranked) > 1 and ranked[1][1] == top:
        return "escalated", None
    if top / sum(counts.values()) >= project.agreement:
        return "agreed", top_label
    return "escalated", None


def resolve(annotations, projects):
    project_of, labels_by_task = {}, defaultdict(list)
    for ann in annotations:
        project_of[ann.task_id] = ann.project
        if not ann.skipped:
            labels_by_task[ann.task_id].append(ann.label)

    results = {}
    for tid in sorted(project_of):
        project = projects[project_of[tid]]
        labels = labels_by_task.get(tid, [])
        # need at least min_votes real votes before deciding
        if len(labels) < project.min_votes:
            results[tid] = TaskResult(tid, project.id, "pending", None, len(labels))
            continue
        status, label = decide(Counter(labels), project)
        results[tid] = TaskResult(tid, project.id, status, label, len(labels))
    return results


def count_labels(results, counts=None):
    """Add the agreed labels in `results` to `counts` (a fresh Counter by default)."""
    if counts is None:
        counts = Counter()
    for result in results:
        if result.status == "agreed":
            counts[result.label] += 1
    return counts
