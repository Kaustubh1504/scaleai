from .enums import Route
from .models import Decision
from .policy import UNKNOWN_SEVERITY


def decide(pred, policy):
    rule = policy.rule_for(pred.label)
    if rule is None:
        return Decision(pred.item_id, Route.EXPERT, "unknown_label", UNKNOWN_SEVERITY)
    severity = rule.severity
    if rule.sensitive:
        return Decision(pred.item_id, Route.EXPERT, "sensitive", severity)
    if pred.flagged:
        return Decision(pred.item_id, policy.fallback(severity), "flagged", severity)
    if pred.confidence is None:
        return Decision(pred.item_id, policy.fallback(severity), "no_confidence", severity)

    if pred.confidence >= policy.threshold_for(rule):
        route, reason = Route.AUTO, "confident"
    else:
        route, reason = policy.fallback(severity), "low_confidence"
    # legacy models may not auto-accept anything
    if route is Route.AUTO and pred.model in policy.legacy_models:
        route, reason = Route.CROWD, "legacy_model"
    return Decision(pred.item_id, route, reason, severity)


def route_all(predictions, policy):
    return {pred.item_id: decide(pred, policy) for pred in predictions}
