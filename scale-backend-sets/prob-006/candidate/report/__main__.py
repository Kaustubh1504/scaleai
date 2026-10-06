"""python -m report --base-url http://127.0.0.1:9300 --out report.json"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

import httpx

from mock_services.clock import RealClock
from report.client import ApiClient, ApiError
from report.report import build_report


def write_atomic(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    with os.fdopen(fd, "w") as fh:
        json.dump(data, fh, indent=2)
    os.replace(tmp, path)


def main(argv: list[str] | None = None, *, http: httpx.Client | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the project throughput report.")
    parser.add_argument("--base-url", default="http://127.0.0.1:9300")
    parser.add_argument("--client-id", default=os.environ.get("PROJECTS_CLIENT_ID", "client"))
    parser.add_argument("--client-secret", default=os.environ.get("PROJECTS_CLIENT_SECRET", "secret"))
    parser.add_argument("--out", type=Path, default=Path("report.json"))
    args = parser.parse_args(argv)

    http = http or httpx.Client(base_url=args.base_url)
    try:
        report = build_report(ApiClient(http, args.client_id, args.client_secret, RealClock()))
    except ApiError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    write_atomic(args.out, report)
    print(f"wrote {args.out}: {report['totals']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
