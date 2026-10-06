from .models import Decision


def route_one(pred, table):
    threshold = table.lookup(pred.model_version, pred.label)
    if pred.confidence is None:
        return Decision(pred.item_id, "human", "missing_confidence", threshold)
    if pred.confidence > threshold:
        return Decision(pred.item_id, "auto", "confident", threshold)
    return Decision(pred.item_id, "human", "low_confidence", threshold)


def route_all(predictions, table):
    return {pred.item_id: route_one(pred, table) for pred in predictions}
