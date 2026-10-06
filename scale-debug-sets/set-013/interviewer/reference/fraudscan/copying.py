from collections import defaultdict


# VERIFIED
def norm_answer(text):
    return " ".join((text or "").lower().split()).rstrip(".!?")


def copy_tasks(submissions):
    """task id -> sorted annotators who gave the same answer as someone else on that task."""
    groups = defaultdict(list)
    for sub in submissions:
        groups[(sub.task_id, norm_answer(sub.answer))].append(sub)
    found = defaultdict(set)
    for (task_id, _), group in groups.items():
        who = {s.annotator_id for s in group}
        if len(who) >= 2:
            found[task_id].update(who)
    return {task: sorted(names) for task, names in sorted(found.items())}
