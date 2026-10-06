#!/usr/bin/env python3
"""Verify a practice problem (build-process steps 1-3, plus the step-4 LOC report).

    python tools/verify_problem.py prob-001            # verify one problem
    python tools/verify_problem.py prob-001 prob-002 --mark-verified
    python tools/verify_problem.py --all

Checks
  1. reference/tests pass.
  2. hidden_tests/test_partN.py pass against the reference and fail against
     the untouched starter code (each part must have failures on the starter).
  3. All of the above runs offline (non-loopback sockets are blocked) and the
     reference + hidden suites finish in under 30 seconds.
  4. (report) lines of code the candidate must add: reference minus starter,
     excluding tests, mock_services, blank lines and comments. Budget: 360
     (about 120 per part). Over budget fails verification.

With --mark-verified, a problem whose checks all pass gets status "verified"
in manifest.json; a failing one is set back to "built".
"""

from __future__ import annotations

import argparse
import difflib
import os
import shutil
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))

import manifest  # noqa: E402

TIME_BUDGET_S = 30.0
LOC_BUDGET = 360
PARTS = ("part1", "part2", "part3")


@dataclass
class RunResult:
    label: str
    passed: int
    failed: int
    errors: int
    skipped: int
    seconds: float
    exit_code: int
    output: str

    @property
    def total(self) -> int:
        return self.passed + self.failed + self.errors

    @property
    def green(self) -> bool:
        return self.exit_code == 0 and self.failed == 0 and self.errors == 0 and self.passed > 0


@dataclass
class Report:
    problem: str
    checks: list[tuple[str, bool, str]] = field(default_factory=list)

    def add(self, name: str, ok: bool, detail: str = "") -> None:
        self.checks.append((name, ok, detail))

    @property
    def ok(self) -> bool:
        return all(ok for _, ok, _ in self.checks)


def run_pytest(label: str, targets: list[str], cwd: Path, env_extra: dict[str, str]) -> RunResult:
    with tempfile.TemporaryDirectory() as tmp:
        junit = Path(tmp) / "junit.xml"
        env = {
            **os.environ,
            "PYTHONPATH": os.pathsep.join([str(TOOLS)] + ([os.environ["PYTHONPATH"]] if os.environ.get("PYTHONPATH") else [])),
            "SCALE_SHARED_PATH": str(ROOT),
            "PYTHONDONTWRITEBYTECODE": "1",
            **env_extra,
        }
        cmd = [sys.executable, "-m", "pytest", *targets, "-q", "-p", "no:cacheprovider", "-p", "no_network",
               f"--junitxml={junit}", "-o", "junit_family=xunit2", "-W", "ignore::DeprecationWarning",
               "--basetemp", str(Path(tmp) / "basetemp")]
        start = time.monotonic()
        try:
            proc = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, timeout=120)
            exit_code, output = proc.returncode, proc.stdout + proc.stderr
        except subprocess.TimeoutExpired as exc:
            exit_code, output = -1, f"TIMEOUT after 120s\n{exc.stdout or ''}"
        seconds = time.monotonic() - start
        passed = failed = errors = skipped = 0
        if junit.exists():
            for suite in ET.parse(junit).getroot().iter("testsuite"):
                tests = int(suite.get("tests", 0))
                failed += int(suite.get("failures", 0))
                errors += int(suite.get("errors", 0))
                skipped += int(suite.get("skipped", 0))
                passed += tests - int(suite.get("failures", 0)) - int(suite.get("errors", 0)) - int(suite.get("skipped", 0))
    return RunResult(label, passed, failed, errors, skipped, seconds, exit_code, output)


def code_lines(path: Path) -> list[str]:
    lines = []
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if line and not line.startswith("#"):
            lines.append(line)
    return lines


def solution_files(tree: Path) -> dict[str, Path]:
    files = {}
    for path in tree.rglob("*.py"):
        rel = path.relative_to(tree)
        if rel.parts[0] in ("tests", "mock_services") or path.name == "conftest.py":
            continue
        files[str(rel)] = path
    return files


def added_loc(starter: Path, reference: Path) -> int:
    """Lines present in the reference but not in the starter (per file, via difflib)."""
    starter_files = solution_files(starter)
    total = 0
    for rel, ref_path in solution_files(reference).items():
        ref = code_lines(ref_path)
        old = code_lines(starter_files[rel]) if rel in starter_files else []
        matcher = difflib.SequenceMatcher(a=old, b=ref, autojunk=False)
        total += sum(j2 - j1 for tag, _, _, j1, j2 in matcher.get_opcodes() if tag in ("insert", "replace"))
    return total


def verify(problem_id: str, verbose: bool = False) -> Report:
    report = Report(problem_id)
    pdir = ROOT / problem_id
    candidate, interviewer = pdir / "candidate", pdir / "interviewer"
    reference, hidden = interviewer / "reference", interviewer / "hidden_tests"

    required = [pdir / "problem.json", candidate / "PART1.md", candidate / "PART2.md", candidate / "PART3.md",
                candidate / "data", candidate / "mock_services", interviewer / "INTERVIEWER_NOTES.md",
                interviewer / "RUBRIC.md", reference / "tests", *[hidden / f"test_{p}.py" for p in PARTS]]
    missing = [str(p.relative_to(ROOT)) for p in required if not p.exists()]
    report.add("layout", not missing, "missing: " + ", ".join(missing) if missing else "all required files present")
    if missing:
        return report

    timed = 0.0
    ref_tests = run_pytest("reference tests", ["tests"], reference, {})
    timed += ref_tests.seconds
    report.add("1. reference tests pass", ref_tests.green,
               f"{ref_tests.passed} passed, {ref_tests.failed} failed, {ref_tests.errors} errors ({ref_tests.seconds:.1f}s)")
    if verbose or not ref_tests.green:
        print(ref_tests.output[-4000:])

    with tempfile.TemporaryDirectory() as tmp:
        # Copy the starter so a broken starter cannot write into the repo.
        starter_copy = Path(tmp) / "candidate"
        shutil.copytree(candidate, starter_copy, ignore=shutil.ignore_patterns("__pycache__"))
        for part in PARTS:
            target = [str(hidden / f"test_{part}.py")]
            on_ref = run_pytest(f"hidden {part} vs reference", target, hidden, {"SOLUTION_DIR": str(reference)})
            timed += on_ref.seconds
            report.add(f"2. hidden {part} passes on reference", on_ref.green,
                       f"{on_ref.passed}/{on_ref.total} passed ({on_ref.seconds:.1f}s)")
            if verbose or not on_ref.green:
                print(on_ref.output[-4000:])
            on_starter = run_pytest(f"hidden {part} vs starter", target, hidden, {"SOLUTION_DIR": str(starter_copy)})
            fails = on_starter.failed + on_starter.errors
            report.add(f"2. hidden {part} fails on starter", fails > 0 and on_starter.exit_code != 0,
                       f"{fails}/{on_starter.total} fail, {on_starter.passed} pass")
            if verbose:
                print(on_starter.output[-2000:])

    report.add("3. offline, under 30s", timed < TIME_BUDGET_S, f"{timed:.1f}s for reference + hidden suites")

    loc = added_loc(candidate, reference)
    report.add("4. reference LOC to add <= 360", loc <= LOC_BUDGET, f"{loc} lines")
    return report


def print_report(report: Report) -> None:
    print(f"\n== {report.problem}: {'PASS' if report.ok else 'FAIL'}")
    for name, ok, detail in report.checks:
        print(f"  [{'ok' if ok else 'XX'}] {name:<36} {detail}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("problems", nargs="*")
    parser.add_argument("--all", action="store_true", help="verify every problem directory that exists")
    parser.add_argument("--mark-verified", action="store_true")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    problems = sorted(p.name for p in ROOT.glob("prob-*") if p.is_dir()) if args.all else args.problems
    if not problems:
        parser.error("name at least one problem or pass --all")
    reports = []
    for problem_id in problems:
        report = verify(problem_id, args.verbose)
        print_report(report)
        reports.append(report)
        if args.mark_verified:
            manifest.set_status(problem_id, "verified" if report.ok else "built")
    print(f"\n{sum(r.ok for r in reports)}/{len(reports)} problems passed verification")
    return 0 if all(r.ok for r in reports) else 1


if __name__ == "__main__":
    sys.exit(main())
