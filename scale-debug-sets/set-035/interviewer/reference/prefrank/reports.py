from pathlib import Path

from .elo import elo_ratings
from .loader import load_comparisons, load_raters
from .stats import win_rates

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
MIN_GAMES = 11


def leaderboard(ratings, games):
    eligible = [m for m in ratings if games[m] >= MIN_GAMES]
    return sorted(eligible, key=lambda m: (-ratings[m], m))


def build_report(data_dir=None):
    data_dir = Path(data_dir or DATA_DIR)
    raters = load_raters(data_dir / "raters.json")
    comparisons, excluded = load_comparisons(data_dir / "comparisons.csv", raters)
    games, rates = win_rates(comparisons)
    ratings = elo_ratings(comparisons)
    return {
        "excluded": dict(sorted(excluded.items())),
        "games": games,
        "win_rates": rates,
        "elo": {m: round(r, 1) for m, r in sorted(ratings.items())},
        "leaderboard": leaderboard(ratings, games),
    }
