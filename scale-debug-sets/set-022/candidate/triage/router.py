from .models import Decision, Route


def route_one(pred, thresholds):
    threshold = thresholds.for_task(pred.task_type)
    if any(flag in thresholds.always_human for flag in pred.flags):
        return Decision(pred, Route.HUMAN, "flagged", threshold)
    if pred.confidence is None:
        return Decision(pred, Route.HUMAN, "no_score", threshold)
    if pred.confidence > threshold:
        return Decision(pred, Route.AUTO, "confident", threshold)
    return Decision(pred, Route.HUMAN, "low_confidence", threshold)


def route_all(predictions, thresholds):
    return [route_one(pred, thresholds) for pred in predictions]
