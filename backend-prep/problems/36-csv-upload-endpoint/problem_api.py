"""Sample upload for problem 36. Tests and your __main__ block both use these."""

from __future__ import annotations

SAMPLE_CSV = (
    "task_id,annotator_email,label,submitted_at,notes\n"
    "t-001,Ana@Example.com,positive,2024-05-01T10:00:00Z,looks fine\n"
    "t-002,ben@example.com, Neutral ,2024-05-01T12:30:00+02:00,\n"
    "t-003,not-an-email,negative,2024-05-01T11:00:00Z,\n"
    "t-001,cy@example.com,negative,2024-05-01T11:05:00Z,dupe\n"
    "t-004,dee@example.com,spam,2024-05-01T11:10:00Z,\n"
    "t-005,eve@example.com,negative,yesterday,\n"
).encode("utf-8")
