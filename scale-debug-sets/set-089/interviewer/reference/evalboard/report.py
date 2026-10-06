from collections import defaultdict
from pathlib import Path

from .loader import load_benchmarks, load_contest, load_submissions, load_teams
from .ranking import rank_board
from .scoring import benchmark_leaders, composite, team_bests

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def benchmark_stats(submissions, leaders, benchmarks):
    entrants = defaultdict(set)
    for sub in submissions:
        if sub.benchmark in benchmarks:
            entrants[sub.benchmark].add(sub.team)
    return {
        name: {"teams": len(entrants[name]), "leader": leaders[name][0], "best": leaders[name][1]}
        for name in sorted(leaders)
    }


def build_leaderboard(data_dir=None):
    data_dir = Path(data_dir or DATA_DIR)
    start, end = load_contest(data_dir / "contest.json")
    teams = load_teams(data_dir / "teams.json")
    benchmarks = load_benchmarks(data_dir / "benchmarks.csv")
    submissions = [s for s in load_submissions(data_dir / "submissions.csv", start, end)
                   if teams.get(s.team) == "active"]
    bests, last_seen = team_bests(submissions, benchmarks)
    leaders = benchmark_leaders(bests, benchmarks)
    rows = [{"team": team, "composite": composite(scores, leaders, benchmarks), "bests": scores}
            for team, scores in bests.items()]
    return {
        "board": rank_board(rows, last_seen),
        "benchmarks": benchmark_stats(submissions, leaders, benchmarks),
        "excluded_teams": sorted(t for t, status in teams.items() if status != "active"),
    }
