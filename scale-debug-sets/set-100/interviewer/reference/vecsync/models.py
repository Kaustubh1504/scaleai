from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Document:
    id: str
    title: str
    text: str
    updated: date


@dataclass(frozen=True)
class Batch:
    id: str
    docs: tuple

    @property
    def doc_ids(self):
        return [d.id for d in self.docs]


class EmbeddingError(Exception):
    pass


class CleanupError(Exception):
    pass
