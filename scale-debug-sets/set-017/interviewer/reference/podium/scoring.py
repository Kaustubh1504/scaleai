from collections import defaultdict

from .models import TeamStats


def submission_score(sub):
    """Accuracy as a percentage, 1 decimal place."""
    return round(100 * sub.correct / sub.total, 1)


# VERIFIED
def pick_best(subs):
    return min(subs, key=lambda s: (-submission_score(s), s.submitted_at))


def team_stats(teams, submissions):
    by_team = defaultdict(list)
    for sub in submissions:
        by_team[sub.team_id].append(sub)
    stats = {}
    for team_id, subs in by_team.items():
        team = teams.get(team_id)
        if team is None or team.disqualified:
            continue
        accepted = [s for s in subs if s.accepted]
        if not accepted:
            continue
        best = pick_best(accepted)
        stats[team_id] = TeamStats(team_id, submission_score(best), best.submitted_at, len(accepted))
    return stats
