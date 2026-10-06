"""Load data/tasks_seed.json into a running service.

    uvicorn --factory app.main:create_app --port 8000 &
    python scripts/seed.py [--url http://localhost:8000] [--file data/tasks_seed.json]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import httpx

HERE = Path(__file__).resolve().parent.parent


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--file", type=Path, default=HERE / "data" / "tasks_seed.json")
    args = parser.parse_args()

    resp = httpx.post(f"{args.url}/tasks", json=json.loads(args.file.read_text()), timeout=10)
    resp.raise_for_status()
    body = resp.json()
    print(f"created {len(body['created'])}: {body['created']}")
    for err in body["errors"]:
        print(f"  entry {err['index']}: {err['error']}")


if __name__ == "__main__":
    main()
