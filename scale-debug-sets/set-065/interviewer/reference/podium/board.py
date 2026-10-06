"""Build the public leaderboard."""
from __future__ import annotations

from podium.loader import load_submissions, load_teams
from podium.ranking import competition_ranks, order
from podium.scoring import best_per_task, overall, tasks_attempted

PODIUM_SIZE = 3


def build_board() -> dict:
    teams = load_teams()
    subs = load_submissions(teams)
    best = best_per_task(subs)
    attempted = tasks_attempted(subs)

    rows = [
        {
            "team_id": tid,
            "name": info["name"],
            "division": info["division"],
            "score": overall(best.get(tid, {})),
            "best": dict(sorted(best.get(tid, {}).items())),
            "tasks_attempted": attempted.get(tid, 0),
        }
        for tid, info in teams.items()
    ]
    ranked = order(rows)
    for row, rank in zip(ranked, competition_ranks(ranked)):
        row["rank"] = rank

    podiums = {}
    for division in sorted({r["division"] for r in ranked}):
        members = [r for r in ranked if r["division"] == division]
        podiums[division] = [r["team_id"] for r in members[:PODIUM_SIZE]]
    return {
        "leaderboard": ranked,
        "podiums": podiums,
        "summary": {
            "teams": len(ranked),
            "counted_submissions": len(subs),
            "submissions_by_task": {t: sum(1 for s in subs if s.task == t) for t in sorted({s.task for s in subs})},
        },
    }
