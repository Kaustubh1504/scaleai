from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class Sample:
    sample_id: str
    group_id: str
    label: str
    created_at: datetime


@dataclass
class LoadResult:
    samples: list = field(default_factory=list)
    excluded: list = field(default_factory=list)
    duplicates: list = field(default_factory=list)
