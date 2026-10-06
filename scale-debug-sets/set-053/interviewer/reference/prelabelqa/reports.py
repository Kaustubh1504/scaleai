from pathlib import Path

from .loader import load_images, load_prelabels, load_reviews
from .review import evaluate

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def build_report(data_dir=None):
    data_dir = Path(data_dir or DATA_DIR)
    images = load_images(data_dir / "images.csv")
    prelabels = load_prelabels(data_dir / "prelabels.json")
    reviews = load_reviews(data_dir / "reviews.csv")
    outcomes, added, out_of_bounds = evaluate(images, prelabels, reviews)
    by_dataset = {}
    for key, outcome in outcomes.items():
        by_dataset.setdefault(images[key.split("/")[0]].dataset, {})[key] = outcome
    return {
        "outcomes": dict(sorted(by_dataset.items())),
        "added": added,
        "out_of_bounds": out_of_bounds,
    }
