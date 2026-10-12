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


def parse_records(raw: list) -> tuple[list[Annotator], list[dict]]:
    raise NotImplementedError


if __name__ == "__main__":
    from problem_api import RAW_RECORDS

    ok, bad = parse_records(RAW_RECORDS)
    for a in ok:
        print(a.model_dump())
    for e in bad:
        print(e)
