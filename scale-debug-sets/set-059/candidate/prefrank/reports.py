from itertools import groupby
from pathlib import Path

from .loader import load_raters, read_comparisons
from .prefs import latest_only
from .ratings import elo, win_rates

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _group_key(c):
    return (c.prompt_id, c.pair)


def contested(comparisons):
    """Prompts where raters picked different outcomes for the same pair."""
    found = set()
    for (prompt_id, _pair), group in groupby(comparisons, key=_group_key):
        if len({c.winner for c in group}) > 1:
            found.add(prompt_id)
    return sorted(found)


def build_report(data_dir=DATA_DIR):
    data_dir = Path(data_dir)
    qualified = load_raters(data_dir / "raters.json")
    comparisons = latest_only(read_comparisons(data_dir / "comparisons.csv", qualified))
    ratings = elo(comparisons)
    return {
        "used": len(comparisons),
        "win_rates": win_rates(comparisons),
        "elo": ratings,
        "leaderboard": sorted(ratings, key=lambda m: (-ratings[m], m)),
        "contested": contested(comparisons),
    }
