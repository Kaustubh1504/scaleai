DEFAULT_THRESHOLD = 0.90
WILDCARD = "*"


class ThresholdTable:
    """Minimum auto-accept confidence per (model_version, label)."""

    def __init__(self, rows):
        self._rows = dict(rows)
        self._cache = {}

    def _resolve(self, model_version, label):
        if (model_version, label) in self._rows:
            return self._rows[(model_version, label)]
        if (model_version, WILDCARD) in self._rows:
            return self._rows[(model_version, WILDCARD)]
        return DEFAULT_THRESHOLD

    def lookup(self, model_version, label):
        key = (model_version, label)
        if key not in self._cache:
            self._cache[key] = self._resolve(model_version, label)
        return self._cache[key]
