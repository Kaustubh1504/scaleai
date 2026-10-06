from pathlib import Path

from .loader import load_submissions, load_teams
from .scoring import team_stats

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def rank(stats):
    # highest score first; on a tie, whoever got there first
    ordered = sorted(stats.values(), key=lambda s: (-s.best_score, s.best_at, s.team_id))
    return [(position, s.team_id) for position, s in enumerate(ordered, start=1)]


def build_report(data_dir=None):
    data_dir = Path(data_dir or DATA_DIR)
    teams = load_teams(data_dir / "teams.json")
    stats = team_stats(teams, load_submissions(data_dir / "submissions.csv"))
    return {
        "teams": {tid: {"best_score": s.best_score, "accepted": s.accepted} for tid, s in sorted(stats.items())},
        "leaderboard": [[position, tid] for position, tid in rank(stats)],
    }
