"""Request and response models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

# Task ids end up in URLs; keep them boring.
TASK_ID_PATTERN = r"^[A-Za-z0-9_-]{1,64}$"


class NewTask(BaseModel):
    """One entry of a POST /tasks batch."""

    model_config = ConfigDict(extra="ignore")

    id: str | None = Field(default=None, pattern=TASK_ID_PATTERN)
    data: dict[str, Any]
    labels: list[str] = Field(min_length=1)
    # Known answer for gold (quality-check) tasks. Never shown to annotators.
    gold_label: str | None = None

    @field_validator("labels")
    @classmethod
    def _labels_are_distinct_and_non_empty(cls, labels: list[str]) -> list[str]:
        if any(not label.strip() for label in labels):
            raise ValueError("labels must be non-empty strings")
        if len(set(labels)) != len(labels):
            raise ValueError("labels must be distinct")
        return labels

    @model_validator(mode="after")
    def _gold_label_is_allowed(self) -> "NewTask":
        if self.gold_label is not None and self.gold_label not in self.labels:
            raise ValueError("gold_label must be one of labels")
        return self


class TaskBatch(BaseModel):
    # Entries are validated one at a time (see parse_entry) so that one bad
    # entry does not reject the whole batch.
    tasks: list[Any]


class SubmitRequest(BaseModel):
    label: str


def parse_entry(entry: Any) -> tuple[NewTask | None, str | None]:
    """Validate one batch entry. Returns (task, None) or (None, error message)."""
    try:
        return NewTask.model_validate(entry), None
    except ValidationError as exc:
        message = "; ".join(
            f"{'.'.join(str(p) for p in err['loc']) or 'entry'}: {err['msg']}" for err in exc.errors()
        )
        return None, message
