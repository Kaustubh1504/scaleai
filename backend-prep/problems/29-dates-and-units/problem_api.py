"""Sample data for problem 29: rows from an annotator time-tracking export, values exactly as received."""

from __future__ import annotations

SAMPLE_ROWS = [
    {"started_at": "2024-03-01T10:00:00Z", "duration": "90s", "payout": "$12.30",
     "shift_start": "2024-03-01 09:00", "tz": "America/New_York"},
    {"started_at": "2024-03-01T12:00:00+05:30", "duration": "1.5m", "payout": "1230c",
     "shift_start": "2024-03-10 02:30", "tz": "America/New_York"},
    {"started_at": "03/01/2024 14:15", "duration": "01:30:00", "payout": "12",
     "shift_start": "2024-11-03 01:30", "tz": "America/New_York"},
    {"started_at": 1709290800, "duration": "1500ms", "payout": 19.99,
     "shift_start": "2024-07-01 09:00", "tz": "Asia/Kolkata"},
    {"started_at": "1709290800123", "duration": "1h30m", "payout": "USD 1,000.00",
     "shift_start": "2024-07-01 09:00", "tz": "Mars/Olympus_Mons"},
    {"started_at": "yesterday", "duration": "-5s", "payout": "$12.345",
     "shift_start": "2024-07-01T09:00:00+02:00", "tz": "Europe/London"},
]
