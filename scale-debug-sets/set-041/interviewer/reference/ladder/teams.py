from .loader import load_contributors, load_submissions
from .scoring import leaderboard

TOP_MEMBERS = 2


def team_standings(rows, roster):
    scores = {row.contributor_id: row.score for row in rows}
    members = {}
    for person in roster.values():
        if not person.team or person.banned:
            continue
        members.setdefault(person.team, []).append(scores.get(person.id, 0))
    table = [
        {"team": team, "score": sum(sorted(pts, reverse=True)[:TOP_MEMBERS]), "members": len(pts)}
        for team, pts in members.items()
    ]
    # highest score first; equal scores in team-name order
    table.sort(key=lambda t: (-t["score"], t["team"]))
    return table


def build_report(contributors_path=None, submissions_path=None):
    roster = load_contributors(contributors_path)
    rows, counted = leaderboard(load_submissions(submissions_path), roster)
    teams = team_standings(rows, roster)
    return {
        "leaderboard": [row.as_dict() for row in rows],
        "teams": teams,
        "summary": {
            "submissions_counted": len(counted),
            "contributors_ranked": len(rows),
            "leader": rows[0].contributor_id if rows else None,
            "top_team": teams[0]["team"] if teams else None,
        },
    }
