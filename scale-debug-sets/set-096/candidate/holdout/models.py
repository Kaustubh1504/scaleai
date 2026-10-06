from dataclasses import dataclass, field
from datetime import date

SPLITS = ("train", "val", "test")


@dataclass(frozen=True)
class Sample:
    sample_id: str
    doc: str
    label: str
    text: str
    quality: float | None
    created: date


@dataclass(frozen=True)
class Source:
    doc: str
    license: str


@dataclass
class DatasetConfig:
    name: str
    file: str
    fractions: dict
    min_quality: float
    blocked_licenses: frozenset
    pins: dict = field(default_factory=dict)
