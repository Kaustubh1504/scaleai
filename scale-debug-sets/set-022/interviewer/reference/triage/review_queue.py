from .models import Route


def queue_key(decision):
    pred = decision.prediction
    score = -1.0 if pred.confidence is None else pred.confidence
    # most urgent first, then the least confident
    return (-pred.priority, score, pred.pred_id)


def build_queue(decisions):
    pending = [d for d in decisions if d.route is Route.HUMAN]
    return sorted(pending, key=queue_key)
