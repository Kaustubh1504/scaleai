from .enums import Route
from .models import LabelRule

UNKNOWN_SEVERITY = 3
EXPERT_MIN_SEVERITY = 3


class Policy:
    def __init__(self, rules, default_threshold, legacy_models):
        self.rules = rules
        self.default_threshold = default_threshold
        self.legacy_models = legacy_models

    def rule_for(self, label):
        return self.rules.get(label)

    def threshold_for(self, rule: LabelRule):
        return rule.threshold if rule.threshold is not None else self.default_threshold

    def fallback(self, severity):
        """Where a prediction goes when it cannot be auto-accepted."""
        return Route.EXPERT if severity >= EXPERT_MIN_SEVERITY else Route.CROWD
