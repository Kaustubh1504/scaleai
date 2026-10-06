from datetime import datetime

from .models import Standing

SEASON_START = datetime(2026, 4, 1)
SEASON_END = datetime(2026, 4, 15)


def in_season(when):
    return SEASON_START <= when < SEASON_END


def eligible(submissions, roster):
    kept = []
    for sub in submissions:
        person = roster.get(sub.contributor_id)
        if person is None or person.banned:
            break
        if not in_season(sub.submitted_at):
            continue
        kept.append(sub)
    return kept


def best_per_task(submissions):
    best = {}
    for sub in submissions:
        per_task = best.setdefault(sub.contributor_id, {})
        per_task[sub.task_id] = max(per_task.get(sub.task_id, 0), sub.points)
    return best


# VERIFIED
def assign_ranks(standings):
    rank, previous = 0, None
    for i, row in enumerate(standings):
        key = (row.score, row.attempts)
        if key != previous:
            rank = i + 1
            previous = key
        row.rank = rank
    return standings


def leaderboard(submissions, roster):
    subs = eligible(submissions, roster)
    best = best_per_task(subs)
    attempts = {}
    for sub in subs:
        attempts[sub.contributor_id] = attempts.get(sub.contributor_id, 0) + 1
    rows = [
        Standing(
            contributor_id=cid,
            name=roster[cid].name,
            score=sum(tasks.values()),
            tasks_solved=sum(1 for pts in tasks.values() if pts > 0),
            attempts=attempts[cid],
        )
        for cid, tasks in best.items()
    ]
    rows.sort(key=lambda r: (-r.score, r.attempts, r.contributor_id))
    return assign_ranks(rows), subs
