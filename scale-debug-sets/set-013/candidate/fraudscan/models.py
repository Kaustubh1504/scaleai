from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class Submission:
    submission_id: str
    annotator_id: str
    task_id: str
    started_at: datetime
    submitted_at: datetime
    answer: str


@dataclass
class AnnotatorReport:
    annotator_id: str
    submissions: int = 0
    fast: int = 0
    flags: set = field(default_factory=set)

    @property
    def fast_ratio(self):
        return round(self.fast / self.submissions, 3) if self.submissions else 0.0
