class Memo:
    """A tiny per-run memo table."""

    def __init__(self):
        self._store = {}
        self.misses = 0

    def get_or_compute(self, key, compute):
        if key not in self._store:
            self.misses += 1
            self._store[key] = compute()
        return self._store[key]
