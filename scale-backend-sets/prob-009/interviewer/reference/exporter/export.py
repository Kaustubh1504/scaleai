"""Export each project's tasks to out_dir as JSONL, plus a manifest, crash-safely and resumably."""

from __future__ import annotations

import hashlib
import json
import random
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import httpx

from exporter.client import NotFoundError, RetriesExhausted, TasksClient
from exporter.files import atomic_writer, sha256_file, write_atomic
from mock_services.clock import Clock

PROJECT_ID = re.compile(r"[A-Za-z0-9_-]+")
MANIFEST = "manifest.json"


@dataclass
class ExportSummary:
    generated_at: str                                       # ISO-8601 UTC, e.g. "2024-05-01T08:00:00Z"
    projects: dict[str, dict] = field(default_factory=dict)  # project_id -> manifest entry

    @property
    def ok(self) -> bool:
        return all(entry.get("status") == "complete" for entry in self.projects.values())


class Exporter:
    def __init__(self, http: httpx.Client, api_key: str, clock: Clock, out_dir: str | Path,
                 rng: random.Random | None = None):
        self.http = http
        self.api_key = api_key
        self.clock = clock
        self.out_dir = Path(out_dir)
        self.client = TasksClient(http, api_key, clock, rng=rng)

    def export(self, project_ids: Iterable[str]) -> ExportSummary:
        ids = list(project_ids)
        bad = [p for p in ids if not isinstance(p, str) or not PROJECT_ID.fullmatch(p)]
        if bad:
            raise ValueError(f"invalid project id(s): {bad!r}")
        generated_at = datetime.fromtimestamp(self.clock.time(), timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        self.out_dir.mkdir(parents=True, exist_ok=True)
        previous = self._previous_entries()
        summary = ExportSummary(generated_at)
        for project_id in ids:
            old = previous.get(project_id)
            if self._still_valid(project_id, old):
                summary.projects[project_id] = old
            else:
                summary.projects[project_id] = self._export_project(project_id)
        write_atomic(self.out_dir / MANIFEST, (json.dumps(asdict(summary), indent=2) + "\n").encode())
        return summary

    # ------------------------------------------------------------- one project

    def _export_project(self, project_id: str) -> dict:
        path = self.out_dir / f"{project_id}.jsonl"
        digest, count = hashlib.sha256(), 0
        try:
            with atomic_writer(path) as fh:
                for page in self.client.iter_task_pages(project_id):
                    for record in page:
                        line = (json.dumps(record) + "\n").encode()
                        fh.write(line)
                        digest.update(line)
                        count += 1
        except NotFoundError:
            path.unlink(missing_ok=True)
            return {"status": "not_found"}
        except RetriesExhausted as exc:
            path.unlink(missing_ok=True)
            return {"status": "failed", "error": str(exc)}
        return {"status": "complete", "tasks": count, "file": path.name, "sha256": digest.hexdigest()}

    # ------------------------------------------------------------- resume

    def _previous_entries(self) -> dict[str, dict]:
        try:
            data = json.loads((self.out_dir / MANIFEST).read_text())
            projects = data["projects"]
        except (FileNotFoundError, ValueError, KeyError, TypeError):
            return {}
        return {k: v for k, v in projects.items() if isinstance(v, dict)} if isinstance(projects, dict) else {}

    def _still_valid(self, project_id: str, entry: dict | None) -> bool:
        if not entry or entry.get("status") != "complete" or entry.get("file") != f"{project_id}.jsonl":
            return False
        actual = sha256_file(self.out_dir / entry["file"])
        return actual is not None and actual == entry.get("sha256")
