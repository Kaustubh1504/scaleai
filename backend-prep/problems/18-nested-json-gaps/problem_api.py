"""Sample annotator records for problem 18: three API versions, all mixed together."""

from __future__ import annotations

RECORDS: list[dict] = [
    # v1: flat
    {"id": "ann_001", "name": "Priya Raman", "email": "Priya@Example.com ", "country": "in",
     "city": "Pune", "skills": "ner, sentiment , ", "rating": "4.8", "active": True},
    # v2: nested profile / contact / address
    {"annotator_id": 2, "profile": {"full_name": "Diego Alvarez", "skills": ["audio", " ocr "]},
     "contact": {"email": "diego@example.com"}, "address": {"country": "MX", "city": "Monterrey"},
     "stats": {"rating": 4.1}, "status": "Active"},
    # v3: split names, a list of addresses, string booleans, lots of gaps
    {"id": "ann_003", "name": "null", "profile": {"full_name": "", "first_name": "Mei", "last_name": "Lin"},
     "email": None, "contact": {"email": "MEI@EXAMPLE.COM"}, "addresses": [{"country": "sg", "city": None}],
     "rating": "n/a", "stats": {"rating": "3"}, "active": "false"},
    # a record with almost nothing in it
    {"id": " ann_004 ", "profile": None, "address": "unknown", "status": "suspended"},
]
