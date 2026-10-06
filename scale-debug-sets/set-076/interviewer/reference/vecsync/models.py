from dataclasses import dataclass
from datetime import date
from enum import Enum


class BatchStatus(Enum):
    OK = "ok"
    FAILED = "failed"
    REJECTED = "rejected"


# Batches whose documents go back on the queue for the next run.
REQUEUE_STATUSES = (BatchStatus.FAILED, BatchStatus.REJECTED)


@dataclass(frozen=True)
class Collection:
    name: str
    dimensions: int
    enabled: bool


@dataclass(frozen=True)
class Document:
    doc_id: str
    collection: str
    text: str
    updated_at: date


@dataclass(frozen=True)
class Batch:
    batch_id: str
    collection: str
    documents: tuple

    @property
    def doc_ids(self):
        return [d.doc_id for d in self.documents]


@dataclass
class BatchResult:
    batch_id: str
    collection: str
    doc_ids: list
    status: BatchStatus
    http_status: int | None = None
