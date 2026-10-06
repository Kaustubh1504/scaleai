import hashlib


class VectorCache:
    """In-memory embedding cache shared by every model run in a batch job."""

    def __init__(self):
        self._store = {}

    @staticmethod
    def key(model, text):
        return hashlib.sha1(text.encode()).hexdigest()

    def get(self, model, text):
        return self._store.get(self.key(model, text))

    def put(self, model, text, vector):
        self._store[self.key(model, text)] = list(vector)

    def __contains__(self, item):
        model, text = item
        return self.key(model, text) in self._store
