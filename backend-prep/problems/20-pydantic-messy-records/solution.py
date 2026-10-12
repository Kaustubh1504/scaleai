"""20. Validating messy records with Pydantic: reference solution."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field, ValidationError, field_validator


class Annotator(BaseModel):
    # Field order is the order pydantic validates (and reports errors) in.
    id: str
    email: str
    age: Optional[int] = Field(default=None, ge=16, le=99)
    tags: list[str] = Field(default_factory=list)
    joined_at: datetime

    @field_validator("id")
    @classmethod
    def _id(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("id must not be blank")
        return v.strip()

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        v = v.strip().lower()
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", v):
            raise ValueError("not a valid email address")
        return v

    @field_validator("age", mode="before")
    @classmethod
    def _age(cls, v: Any) -> Any:
        if isinstance(v, str):
            v = v.strip()
            if v.isdigit():
                return int(v)
        if v is None or v == "":
            return None
        if type(v) is not int:  # rejects bool too
            raise ValueError("age must be a whole number")
        return v

    @field_validator("tags", mode="before")
    @classmethod
    def _tags(cls, v: Any) -> Any:
        if v is None:
            return []
        if isinstance(v, str):
            v = v.split(",")
        if not isinstance(v, list) or not all(isinstance(t, str) for t in v):
            raise ValueError("tags must be a comma-separated string or a list of strings")
        return list(dict.fromkeys(t.strip().lower() for t in v if t.strip()))

    @field_validator("joined_at", mode="before")
    @classmethod
    def _joined_at_is_str(cls, v: Any) -> Any:
        if not isinstance(v, str):
            raise ValueError("joined_at must be an ISO 8601 string")
        return v

    @field_validator("joined_at")
    @classmethod
    def _joined_at_utc(cls, v: datetime) -> datetime:
        return v.replace(tzinfo=timezone.utc) if v.tzinfo is None else v.astimezone(timezone.utc)


def parse_records(raw: list) -> tuple[list[Annotator], list[dict]]:
    valid, errors = [], []
    for i, item in enumerate(raw):
        try:
            valid.append(Annotator.model_validate(item))
        except ValidationError as exc:
            first = exc.errors()[0]
            field = str(first["loc"][0]) if first["loc"] else None
            errors.append({"index": i, "field": field, "message": first["msg"]})
    return valid, errors


if __name__ == "__main__":
    from problem_api import RAW_RECORDS

    ok, bad = parse_records(RAW_RECORDS)
    for a in ok:
        print(a.model_dump())
    for e in bad:
        print(e)
