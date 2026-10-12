"""Sample annotator sign-up records for problem 20 (as exported from three intake forms)."""

from __future__ import annotations

RAW_RECORDS: list = [
    {"id": " ann_101 ", "email": "Priya.Raman@Example.COM", "age": "29", "tags": "NER, sentiment, ner",
     "joined_at": "2024-03-01T10:00:00Z", "referrer": "campus"},
    {"id": "ann_102", "email": "diego@example.com", "age": 41, "tags": ["audio", " OCR "],
     "joined_at": "2024-03-01T12:30:00+02:00"},
    {"id": "ann_103", "email": "mei@example", "age": "35", "joined_at": "2024-03-02T08:00:00"},
    {"id": "ann_104", "email": "sam@example.com", "age": "42.5", "joined_at": "2024-03-02T09:00:00Z"},
    {"id": "   ", "email": "blank@example.com", "joined_at": "2024-03-03T00:00:00Z"},
    {"id": "ann_106", "email": "ana@example.com", "age": True, "tags": None, "joined_at": "2024-03-03T09:15:00-05:00"},
    "ann_107,fatima@example.com,30",
    {"id": "ann_108", "email": "jonas@example.com", "age": "", "joined_at": "yesterday"},
    {"id": "ann_109", "email": " JONAS.B@EXAMPLE.COM ", "age": None, "tags": [], "joined_at": "2024-03-04T18:45:00+05:30"},
]
