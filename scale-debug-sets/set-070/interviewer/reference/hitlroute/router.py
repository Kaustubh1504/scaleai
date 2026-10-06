from .models import Decision, Routed


def route(pred, policy):
    """Decide whether a model prediction can be accepted or needs a human."""
    if pred.sensitive:
        return Routed(pred, Decision.HUMAN_REVIEW, "sensitive")
    if pred.label in policy.always_review:
        return Routed(pred, Decision.HUMAN_REVIEW, "label_policy")
    if pred.confidence is None:
        return Routed(pred, Decision.HUMAN_REVIEW, "no_confidence")
    if pred.confidence < policy.threshold:
        return Routed(pred, Decision.HUMAN_REVIEW, "low_confidence")
    return Routed(pred, Decision.AUTO_ACCEPT, "confident")


def route_all(preds, policies):
    return [route(p, policies[p.task]) for p in preds]
