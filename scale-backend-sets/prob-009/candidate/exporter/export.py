"""Export each project's tasks to out_dir (see PART1.md)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

import httpx

from mock_services.clock import Clock


@dataclass
class ExportSummary:
    generated_at: str                                       # ISO-8601 UTC, e.g. "2024-05-01T08:00:00Z"
    projects: dict[str, dict] = field(default_factory=dict)  # project_id -> manifest entry

    @property
    def ok(self) -> bool:
        return all(entry.get("status") == "complete" for entry in self.projects.values())


class Exporter:
    def __init__(self, http: httpx.Client, api_key: str, clock: Clock, out_dir: str | Path):
        self.http = http
        self.api_key = api_key
        self.clock = clock
        self.out_dir = Path(out_dir)

    def export(self, project_ids: Iterable[str]) -> ExportSummary:
        raise NotImplementedError
