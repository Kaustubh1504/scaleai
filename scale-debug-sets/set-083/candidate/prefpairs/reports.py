from pathlib import Path

from .aggregate import aggregate
from .leaderboard import export_pairs, standings
from .loader import latest_only, load_judgements, load_labelers, load_pairs
from .quality import labeler_quality

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def build_report(data_dir=None):
    data_dir = Path(data_dir or DATA_DIR)
    active = load_labelers(data_dir / "labelers.json")
    pairs = load_pairs(data_dir / "pairs.csv")
    calibration = load_judgements(data_dir / "calibration.csv")
    judgements = latest_only(load_judgements(data_dir / "judgements.csv"))

    quality = labeler_quality(calibration, pairs, active)
    counted = {lab for lab, row in quality.items() if not row["excluded"]}
    results = aggregate(judgements, pairs, counted)
    return {
        "labelers": quality,
        "pairs": results,
        "dataset": export_pairs(results, pairs),
        "standings": standings(results, pairs),
    }
