#!/usr/bin/env python3
"""Copy a problem's candidate folder plus shared/ into a standalone directory.

    python tools/export_candidate.py prob-001 ~/interview
    # -> ~/interview/prob-001/ (what the candidate gets) and ~/interview/shared/

Hand the candidate PART1.md first; keep PART2.md and PART3.md back until they
finish the previous part (the export includes them; remove them with --part1-only).
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache", "tests")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("problem")
    parser.add_argument("dest", type=Path)
    parser.add_argument("--part1-only", action="store_true", help="leave out PART2.md and PART3.md")
    args = parser.parse_args(argv)

    dest = args.dest.expanduser().resolve()
    target = dest / args.problem
    if target.exists():
        raise SystemExit(f"{target} already exists")
    shutil.copytree(ROOT / args.problem / "candidate", target,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache"))
    if args.part1_only:
        for name in ("PART2.md", "PART3.md"):
            (target / name).unlink(missing_ok=True)
    if not (dest / "shared").exists():
        shutil.copytree(ROOT / "shared", dest / "shared", ignore=IGNORE)
    print(f"exported {args.problem} to {target}")


if __name__ == "__main__":
    main()
