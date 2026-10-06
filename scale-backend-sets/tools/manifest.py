#!/usr/bin/env python3
"""Read and maintain manifest.json, the resumable index of all 100 problems.

    python tools/manifest.py check              # uniqueness and mix constraints
    python tools/manifest.py table 1 5          # summary table for prob-001..prob-005
    python tools/manifest.py next               # first problem that is not verified
    python tools/manifest.py sync prob-001      # copy fields from prob-001/problem.json into the manifest

Statuses: planned -> built -> verified.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "manifest.json"
STATUSES = ("planned", "built", "verified")
FIELDS = ("id", "title", "kind", "topics", "mode", "difficulty", "status", "starter", "planted_bugs")
KINDS = ("api-client", "service")
MIN_API_CLIENT_SHARE = 0.60


def load() -> dict:
    return json.loads(MANIFEST.read_text())


def save(data: dict) -> None:
    tmp = MANIFEST.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n")
    tmp.replace(MANIFEST)


def entry(data: dict, problem_id: str) -> dict:
    for item in data["problems"]:
        if item["id"] == problem_id:
            return item
    raise KeyError(problem_id)


def set_status(problem_id: str, status: str) -> None:
    if status not in STATUSES:
        raise ValueError(status)
    data = load()
    entry(data, problem_id)["status"] = status
    save(data)


def sync(problem_id: str) -> None:
    """Problem directories are the source of truth for title/topics/mode once built."""
    meta = json.loads((ROOT / problem_id / "problem.json").read_text())
    data = load()
    item = entry(data, problem_id)
    for key in FIELDS:
        if key in meta and key != "status":
            item[key] = meta[key]
    if item["status"] == "planned":
        item["status"] = "built"
    save(data)


def check(data: dict) -> list[str]:
    problems = data["problems"]
    issues = []
    combos = Counter(tuple(sorted(p["topics"])) for p in problems)
    for combo, count in combos.items():
        if count > 1:
            issues.append(f"topic combination used {count} times: {combo}")
    for p in problems:
        if not 2 <= len(p["topics"]) <= 4:
            issues.append(f"{p['id']} has {len(p['topics'])} topics (need 2-4)")
        unknown = set(p["topics"]) - set(data["topics"])
        if unknown:
            issues.append(f"{p['id']} uses unknown topics {sorted(unknown)}")
        n = int(p["id"].split("-")[1])
        expected = "medium" if n <= 20 else "hard" if n <= 70 else "very hard"
        if p["difficulty"] != expected:
            issues.append(f"{p['id']} difficulty {p['difficulty']!r}, expected {expected!r}")
        if p.get("kind") not in KINDS:
            issues.append(f"{p['id']} kind {p.get('kind')!r}, expected one of {KINDS}")
    total = len(problems)
    api = [p for p in problems if p.get("kind") == "api-client"]
    if len(api) / total < MIN_API_CLIENT_SHARE:
        issues.append(f"only {len(api)}/{total} problems are api-client (need >= {MIN_API_CLIENT_SHARE:.0%})")
    repo = [p for p in problems if p["starter"] == "repo"]
    plain = [p for p in problems if p["mode"] != "fastapi"]
    bugs = [p for p in repo if p["planted_bugs"]]
    service_plain = [p for p in problems if p.get("kind") == "service" and p["mode"] != "fastapi"]
    print(f"{total} problems | api-client {len(api)} ({len(api) / total:.0%}, target >=60%) | "
          f"plain-python among services {len(service_plain)}/{total - len(api)}")
    print(f"{total} problems | starter repos {len(repo)} ({len(repo) / total:.0%}, target ~40%) | "
          f"plain-python overall {len(plain)} ({len(plain) / total:.0%}) | "
          f"repos with planted bugs {len(bugs)} ({len(bugs) / max(1, len(repo)):.0%} of repos, target ~30%)")
    unused = set(data["topics"]) - {t for p in problems for t in p["topics"]}
    if unused:
        issues.append(f"topics never used: {sorted(unused)}")
    return issues


def table(data: dict, first: int, last: int) -> str:
    rows = [p for p in data["problems"] if first <= int(p["id"].split("-")[1]) <= last]
    header = ("id", "title", "kind", "topics", "mode", "difficulty", "status")
    body = [(p["id"], p["title"], p.get("kind", ""), ", ".join(p["topics"]), p["mode"], p["difficulty"], p["status"])
            for p in rows]
    widths = [max(len(str(r[i])) for r in [header, *body]) for i in range(len(header))]
    line = lambda r: "| " + " | ".join(str(c).ljust(w) for c, w in zip(r, widths)) + " |"  # noqa: E731
    sep = "|" + "|".join("-" * (w + 2) for w in widths) + "|"
    return "\n".join([line(header), sep, *map(line, body)])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check")
    t = sub.add_parser("table")
    t.add_argument("first", type=int)
    t.add_argument("last", type=int)
    sub.add_parser("next")
    s = sub.add_parser("sync")
    s.add_argument("problems", nargs="+")
    args = parser.parse_args(argv)

    data = load()
    if args.cmd == "check":
        issues = check(data)
        print("\n".join(issues) if issues else "manifest OK")
        return 1 if issues else 0
    if args.cmd == "table":
        print(table(data, args.first, args.last))
    elif args.cmd == "next":
        pending = [p["id"] for p in data["problems"] if p["status"] != "verified"]
        print(pending[0] if pending else "all verified")
    elif args.cmd == "sync":
        for problem_id in args.problems:
            sync(problem_id)
    return 0


if __name__ == "__main__":
    sys.exit(main())
