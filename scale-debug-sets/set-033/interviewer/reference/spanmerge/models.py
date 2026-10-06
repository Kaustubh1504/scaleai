from dataclasses import dataclass

LABELS = ("PER", "ORG", "LOC")


@dataclass(frozen=True)
class Document:
    doc_id: str
    text: str


@dataclass(frozen=True)
class Span:
    doc_id: str
    annotator: str
    start: int
    end: int
    label: str

    @property
    def key(self):
        return (self.doc_id, self.start, self.end, self.label)
