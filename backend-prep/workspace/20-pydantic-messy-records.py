"""20. Validating messy records with Pydantic

Template: imports, constants, exceptions and signatures are here.
Fill in every `raise NotImplementedError` (add your own helpers as needed)."""

from __future__ import annotations
import re
from datetime import datetime, timezone
from typing import Any, Optional
from pydantic import BaseModel, Field, ValidationError, field_validator

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class Annotator(BaseModel):
    # Field order matters: it is the order pydantic validates and reports errors in.
    id: str
    email: str
    age: Optional[int] = Field(default=None, ge=16, le=99)
    tags: list[str] = Field(default_factory=list)
    joined_at: datetime
    
    @field_validator("id")
    @classmethod
    def _id_not_blank(cls, v:str)->str:
        v = v.strip()
        if not v:
            raise ValueError("id must not be black")
        return v
    
    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        v = v.strip().lower()
        if not EMAIL_RE.match(v):
            raise ValueError("not a valid email address")
        return v

    @field_validator("age", mode="before")
    @classmethod
    def _age(cls, v: Any) -> Any:
        if v is None:
            return None
        if isinstance(v, bool):  # bool is a subclass of int: reject it explicitly
            raise ValueError("age must be a whole number, not a bool")
        if isinstance(v, int):
            return v
        if isinstance(v, str):
            s = v.strip()
            if s == "":
                return None
            if s.isdigit():
                return int(s)
        raise ValueError("age must be a whole number")

    @field_validator("tags", mode="before")
    @classmethod
    def _tags(cls, v: Any) -> Any:
        if v is None:
            return []
        if isinstance(v, str):
            v = v.split(",")
        if not isinstance(v, list) or not all(isinstance(t, str) for t in v):
            raise ValueError("tags must be a comma-separated string or a list of strings")
        cleaned = (t.strip().lower() for t in v)
        return list(dict.fromkeys(t for t in cleaned if t))  # dedupe, keep first occurrence

    @field_validator("joined_at", mode="before")
    @classmethod
    def _joined_at_is_string(cls, v: Any) -> Any:
        if not isinstance(v, str):
            raise ValueError("joined_at must be an ISO 8601 string")
        return v

    @field_validator("joined_at")
    @classmethod
    def _joined_at_utc(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v.astimezone(timezone.utc)


def parse_records(raw: list) -> tuple[list[Annotator], list[dict]]:
    valid = []
    errors = []
    
    for index, item in enumerate(raw):
        try:
            valid.append(Annotator.model_validate(item))
        except ValidationError as exc:
            first = exc.errors()[0]
            loc = first["loc"]
            errors.append({"index": index, "field": str(loc[0]) if loc else None, "message": first["msg"]})
    return valid, errors


if __name__ == "__main__":
    from problem_api import RAW_RECORDS

    ok, bad = parse_records(RAW_RECORDS)
    for a in ok:
        print(a.model_dump())
    for e in bad:
        print(e)
