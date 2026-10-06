from collections import Counter
from pathlib import Path

from .elo import elo_ratings
from .loader import load_comparisons, load_models
from .winrates import win_table

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
MIN_GAMES = 4


def leaderboard(table, ratings):
    eligible = [mid for mid, stats in table.items() if stats.games > MIN_GAMES]
    return sorted(eligible, key=lambda mid: (-ratings[mid], mid))


def annotator_activity(comparisons):
    rated = Counter(c.annotator for c in comparisons)
    return {name: rated[name] for name in sorted(rated)}


def build_report(data_dir=None):
    data_dir = Path(data_dir or DATA_DIR)
    registry = load_models(data_dir / "models.json")
    comparisons = load_comparisons(data_dir / "comparisons.csv", registry)
    table = win_table(comparisons, registry)
    ratings = elo_ratings(comparisons, registry)
    played = [mid for mid in registry if table[mid].games]
    return {
        "models": {
            mid: {
                "games": table[mid].games,
                "wins": table[mid].wins,
                "ties": table[mid].ties,
                "win_rate": table[mid].win_rate,
                "elo": round(ratings[mid], 1),
            }
            for mid in played
        },
        "leaderboard": leaderboard(table, ratings),
        "annotators": annotator_activity(comparisons),
        "comparisons_used": len(comparisons),
    }
