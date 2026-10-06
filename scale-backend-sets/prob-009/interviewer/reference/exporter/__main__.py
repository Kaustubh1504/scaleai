"""python -m exporter --project prj_01 --project prj_02 --out exports/

Exit code: 0 if every project is "complete", 2 if some project is not, 1 on a fatal error.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import httpx

from exporter.client import ApiError
from exporter.export import Exporter
from mock_services.clock import Clock, RealClock


def main(argv: list[str] | None = None, *, http: httpx.Client | None = None, clock: Clock | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export each project's tasks as JSONL files plus a manifest.")
    parser.add_argument("--project", action="append", required=True, help="project id (repeatable)")
    parser.add_argument("--out", type=Path, default=Path("exports"))
    parser.add_argument("--base-url", default="http://127.0.0.1:9300")
    parser.add_argument("--api-key", default=os.environ.get("TASKS_API_KEY", "key_live_exporter"))
    args = parser.parse_args(argv)

    http = http or httpx.Client(base_url=args.base_url)
    try:
        summary = Exporter(http, args.api_key, clock or RealClock(), args.out).export(args.project)
    except (ApiError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    for project_id, entry in summary.projects.items():
        detail = entry.get("tasks", entry.get("error", ""))
        print(f"{project_id}: {entry['status']} {detail}".rstrip())
    return 0 if summary.ok else 2


if __name__ == "__main__":
    sys.exit(main())
