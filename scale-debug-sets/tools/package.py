"""Zip each verified set's candidate/ and interviewer/ folders separately.

    python tools/package.py            # all verified sets
    python tools/package.py set-001    # specific sets

Writes dist/<set>-candidate.zip and dist/<set>-interviewer.zip.
"""
from __future__ import annotations

import sys
import zipfile

from common import LIB_ROOT, load_manifest, set_dir

DIST = LIB_ROOT / "dist"
SKIP = {"__pycache__", ".pytest_cache", ".DS_Store"}


def zip_folder(src, dest, arc_root):
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(src.rglob("*")):
            if path.is_file() and not SKIP & set(path.parts) and path.suffix != ".pyc":
                zf.write(path, f"{arc_root}/{path.relative_to(src)}")


def main(argv: list[str]) -> int:
    ids = argv or [s["id"] for s in load_manifest()["sets"] if s["status"] == "verified"]
    DIST.mkdir(exist_ok=True)
    for set_id in ids:
        for part in ("candidate", "interviewer"):
            dest = DIST / f"{set_id}-{part}.zip"
            zip_folder(set_dir(set_id) / part, dest, f"{set_id}-{part}")
            print(f"wrote {dest.relative_to(LIB_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
