from pathlib import Path

from .loader import load_ground_truth, load_images, load_predictions
from .matching import evaluate_model

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _ratio(num, den):
    return round(num / den, 3) if den else 0.0


def build_report(data_dir=None):
    data_dir = Path(data_dir or DATA_DIR)
    images = load_images(data_dir / "images.csv")
    gt = load_ground_truth(data_dir / "ground_truth.csv", images)
    preds = load_predictions(data_dir / "predictions.json", images)

    per_image, models = {}, {}
    for model in sorted(preds):
        counts = evaluate_model(preds[model], gt)
        for image, c in counts.items():
            per_image[f"{model}/{image}"] = {"tp": c.tp, "fp": c.fp, "fn": c.fn}
        tp = sum(c.tp for c in counts.values())
        fp = sum(c.fp for c in counts.values())
        fn = sum(c.fn for c in counts.values())
        precision, recall = _ratio(tp, tp + fp), _ratio(tp, tp + fn)
        models[model] = {
            "tp": tp, "fp": fp, "fn": fn,
            "precision": precision, "recall": recall,
            "f1": round(2 * precision * recall / (precision + recall), 3) if precision + recall else 0.0,
            "auto_accept": sorted(i for i, c in counts.items() if gt[i] and c.fp == 0 and c.fn == 0),
        }
    best = min(models, key=lambda m: (-models[m]["f1"], m)) if models else None
    return {"images": per_image, "models": models, "best_model": best}
