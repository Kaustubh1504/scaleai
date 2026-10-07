"""Shared helpers for the debug-set tooling (manifest IO, bug application, test runs)."""
from __future__ import annotations

import contextlib
import fcntl
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

LIB_ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = LIB_ROOT / "tools"
MANIFEST = LIB_ROOT / "manifest.json"
RUNNER = TOOLS_DIR / "_runner.py"

IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache", ".DS_Store")

# A single test run (whole suite) longer than this is treated as a hang.
SUITE_TIMEOUT_S = 60
# Spec: no individual test may take longer than this.
TEST_LIMIT_S = 2.0


def load_manifest() -> dict:
    if MANIFEST.exists():
        return json.loads(MANIFEST.read_text())
    return {"version": 1, "sets": []}


def save_manifest(manifest: dict) -> None:
    tmp = MANIFEST.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(manifest, indent=2) + "\n")
    tmp.replace(MANIFEST)


@contextlib.contextmanager
def manifest_lock():
    """Serialise read-modify-write of manifest.json across parallel builders."""
    with open(LIB_ROOT / ".manifest.lock", "w") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)


def set_dir(set_id: str) -> Path:
    return LIB_ROOT / set_id


def load_spec(set_id: str) -> dict:
    """The authored bug spec lives next to the answer key."""
    return json.loads((set_dir(set_id) / "interviewer" / "bugs.json").read_text())


def reference_dir(set_id: str) -> Path:
    return set_dir(set_id) / "interviewer" / "reference"


def copy_repo(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst, ignore=IGNORE)


def bug_edits(bug: dict) -> list[dict]:
    """The main (file, old, new) edit plus any `extra` edits (e.g. dropping an import the
    buggy line no longer needs, so no unused name points at the change)."""
    main = {"file": bug["file"], "old": bug["old"], "new": bug["new"]}
    return [main] + [{"file": e.get("file", bug["file"]), "old": e["old"], "new": e["new"]}
                     for e in bug.get("extra", [])]


def apply_bugs(repo: Path, bugs: list[dict]) -> None:
    """Apply each bug's edits in place. Each `old` must match exactly once."""
    for bug in bugs:
        for edit in bug_edits(bug):
            path = repo / edit["file"]
            text = path.read_text()
            count = text.count(edit["old"])
            if count != 1:
                raise ValueError(f"{bug['id']}: old text found {count}x in {edit['file']} (need exactly 1)")
            path.write_text(text.replace(edit["old"], edit["new"], 1))


def run_tests(repo: Path) -> dict:
    """Run the suite in a subprocess. Returns {"tests": {id: {...}}, "timed_out": bool}."""
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONHASHSEED="0")
    try:
        proc = subprocess.run(
            [sys.executable, str(RUNNER), str(repo)],
            cwd=repo, env=env, capture_output=True, text=True, timeout=SUITE_TIMEOUT_S,
        )
    except subprocess.TimeoutExpired:
        return {"tests": {}, "timed_out": True, "stderr": ""}
    try:
        payload = json.loads(proc.stdout.strip().splitlines()[-1])
    except (IndexError, json.JSONDecodeError):
        return {"tests": {}, "timed_out": False, "crashed": True, "stderr": proc.stderr[-4000:]}
    payload["timed_out"] = False
    return payload


def run_with_bugs(set_id: str, bugs: list[dict]) -> dict:
    with tempfile.TemporaryDirectory(prefix=f"{set_id}-") as tmp:
        repo = Path(tmp) / "repo"
        copy_repo(reference_dir(set_id), repo)
        apply_bugs(repo, bugs)
        return run_tests(repo)


def run_pytest(repo: Path) -> tuple[bool, str]:
    """Confirm the suite also collects and runs under pytest (if available)."""
    try:
        import pytest  # noqa: F401
    except ImportError:
        return True, "pytest not installed; skipped"
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests"],
        cwd=repo, env=env, capture_output=True, text=True, timeout=SUITE_TIMEOUT_S,
    )
    return proc.returncode == 0, proc.stdout.strip().splitlines()[-1] if proc.stdout else proc.stderr


def failing(result: dict) -> dict[str, str]:
    """test id -> outcome, for tests that did not pass."""
    return {tid: t["status"] for tid, t in result["tests"].items() if t["status"] != "pass"}


def test_file_of(test_id: str) -> str:
    # ids look like tests.test_1_assignment.TestAssignment.test_x
    parts = test_id.split(".")
    return parts[1] if len(parts) > 1 else test_id


def failing_files(result: dict) -> list[str]:
    return sorted({test_file_of(t) for t in failing(result)})


def signature(result: dict) -> dict[str, tuple[str, str]]:
    """Comparable fingerprint of a run: per-test status and failure message."""
    return {tid: (t["status"], t.get("message", "")) for tid, t in result["tests"].items()}
