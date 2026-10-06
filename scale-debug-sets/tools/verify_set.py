"""Verify one debug set end to end and (re)generate its candidate repo.

    python tools/verify_set.py set-001 [set-002 ...]

Steps (from the build spec):
  1. reference/ passes its own suite under unittest and pytest
  3. mutation check: every bug alone breaks >=1 test; all bugs together give the
     designed failing pattern; masked bugs are invisible while their maskers are
     present (identical per-test status AND failure message)
  4. no test takes over TEST_LIMIT_S and no run hangs
  5. candidate/ = reference + all bugs, then grep it for leftover hints
  6. sync the bug list into manifest.json; status -> verified only if all pass

Writes interviewer/verification.json (observed failures per bug) for the docs.
"""
from __future__ import annotations

import csv
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from common import (
    TEST_LIMIT_S, apply_bugs, copy_repo, manifest_lock, failing, failing_files, load_manifest,
    load_spec, reference_dir, run_pytest, run_tests, run_with_bugs, save_manifest,
    set_dir, signature,
)

HINT_PATTERNS = re.compile(
    r"\b(bugs?|buggy|fixme|todo|xxx|hack|broken(?! by)|intentional(ly)?|injected|mutation|"
    r"off[- ]by[- ]one|wrong|incorrect|deliberate(ly)?)\b",
    re.IGNORECASE,
)
SOURCE_LIMITS = {"MINI": (4, 6), "FULL": (6, 9)}
TEST_FILES = {"MINI": 2, "FULL": 3}
BUG_COUNT = {"MINI": 3, "FULL": 6}
DATA_ROWS = (10, 40)


class Report:
    def __init__(self, set_id: str):
        self.set_id = set_id
        self.problems: list[str] = []
        self.notes: list[str] = []

    def check(self, ok: bool, msg: str) -> bool:
        (self.notes if ok else self.problems).append(("ok   " if ok else "FAIL ") + msg)
        return ok

    def ok(self) -> bool:
        return not self.problems


def _slow_tests(result: dict) -> list[str]:
    return [f"{tid} ({t['duration']}s)" for tid, t in result["tests"].items() if t["duration"] > TEST_LIMIT_S]


def _run_ok(rep: Report, label: str, result: dict) -> bool:
    if result.get("timed_out"):
        return rep.check(False, f"{label}: suite timed out (hang?)")
    if result.get("crashed") or not result["tests"]:
        return rep.check(False, f"{label}: runner crashed: {result.get('stderr', '')[-500:]}")
    slow = _slow_tests(result)
    return rep.check(not slow, f"{label}: no test over {TEST_LIMIT_S}s" + (f" -> {slow}" if slow else ""))


def source_files(repo: Path, package: str) -> list[Path]:
    files = [p for p in (repo / package).rglob("*.py") if p.name != "__init__.py"]
    files += [p for p in repo.glob("*.py")]
    return files


def data_row_counts(repo: Path) -> dict[str, int]:
    counts = {}
    for path in sorted((repo / "data").rglob("*")):
        if path.suffix == ".csv":
            with open(path, newline="", encoding="utf-8-sig") as fh:
                counts[path.name] = max(0, sum(1 for _ in csv.reader(fh)) - 1)
        elif path.suffix in (".json", ".jsonl"):
            text = path.read_text(encoding="utf-8-sig")
            if path.suffix == ".jsonl":
                counts[path.name] = sum(1 for line in text.splitlines() if line.strip())
            else:
                obj = json.loads(text)
                if isinstance(obj, list):
                    counts[path.name] = len(obj)
                elif isinstance(obj, dict):
                    lists = [v for v in obj.values() if isinstance(v, list)]
                    if lists:
                        counts[path.name] = max(len(v) for v in lists)
    return counts


def grep_hints(repo: Path) -> list[str]:
    hits = []
    for path in sorted(repo.rglob("*")):
        if not path.is_file() or path.suffix not in (".py", ".md", ".csv", ".json", ".jsonl", ".txt", ".cfg", ".toml"):
            continue
        for n, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
            if HINT_PATTERNS.search(line):
                hits.append(f"{path.relative_to(repo)}:{n}: {line.strip()[:100]}")
    return hits


def verify(set_id: str) -> Report:
    rep = Report(set_id)
    spec = load_spec(set_id)
    bugs = spec["bugs"]
    length = spec["length"]
    ref = reference_dir(set_id)
    observed: dict[str, dict] = {}

    # ---- structure -----------------------------------------------------------
    rep.check(len(bugs) == BUG_COUNT[length], f"{len(bugs)} bugs for {length}")
    tests = sorted(p.stem for p in (ref / "tests").glob("test_*.py"))
    rep.check(len(tests) == TEST_FILES[length], f"{len(tests)} test files for {length}")
    lo, hi = SOURCE_LIMITS[length]
    n_src = len(source_files(ref, spec["package"]))
    rep.check(lo <= n_src <= hi, f"{n_src} source files (want {lo}-{hi})")
    files = {b["file"] for b in bugs}
    rep.check(len(files) >= (len(bugs) + 1) // 2, f"bugs spread over {len(files)} files")
    fmt = spec.get("format", "multi")
    planned = next((e.get("format") for e in load_manifest()["sets"] if e["id"] == set_id), fmt)
    rep.check(fmt == planned, f"format {fmt} (manifest plan: {planned})")
    if fmt == "one_to_one":
        last_file = tests[-1] if tests else ""
        rep.check(all(b.get("test") for b in bugs), "every bug names its failing test")
        rep.check(len({b.get("test") for b in bugs}) == len(bugs), "bug tests are distinct")
        rep.check(not any(b.get("masked_by") for b in bugs), "no masked_by in one_to_one (would break 1:1)")
        rep.check(any(b.get("test", "").startswith(last_file + ".") for b in bugs),
                  f"at least one bug only surfaces in the last test file ({last_file})")
    else:
        rep.check(any(b.get("masked_by") or b.get("visible_only_in") for b in bugs), "at least one masked bug")
    qa = spec.get("context_qa", [])
    rep.check(5 <= len(qa) <= 8, f"{len(qa)} context-assistant Q&As (want 5-8)")
    for name, rows in data_row_counts(ref).items():
        rep.check(DATA_ROWS[0] <= rows <= DATA_ROWS[1], f"data/{name}: {rows} rows")
    rep.check((ref / "README.md").exists(), "README.md present")

    # ---- step 1: reference passes ---------------------------------------------
    base = run_tests(ref)
    if _run_ok(rep, "reference", base):
        rep.check(not failing(base), f"reference passes all {len(base['tests'])} tests"
                  + (f" -> failing {failing(base)}" if failing(base) else ""))
    ok, line = run_pytest(ref)
    rep.check(ok, f"reference under pytest: {line}")

    # ---- step 3: mutation check ---------------------------------------------
    by_id = {b["id"]: b for b in bugs}
    for bug in bugs:
        try:
            res = run_with_bugs(set_id, [bug])
        except ValueError as exc:
            rep.check(False, str(exc))
            continue
        _run_ok(rep, f"{bug['id']} alone", res)
        ff = failing_files(res)
        observed[bug["id"]] = {
            "failing_files": ff,
            "failures": {tid: res["tests"][tid].get("message", "")[:600] for tid in failing(res)},
        }
        rep.check(bool(ff), f"{bug['id']} alone breaks {ff}")
        only = bug.get("visible_only_in")
        if only:
            rep.check(set(ff) <= set(only), f"{bug['id']} visible only in {only} (got {ff})")
        maskers = bug.get("masked_by")
        if maskers:
            masked_run = run_with_bugs(set_id, [by_id[m] for m in maskers])
            both_run = run_with_bugs(set_id, [by_id[m] for m in maskers] + [bug])
            same = signature(masked_run) == signature(both_run)
            rep.check(same, f"{bug['id']} hidden while {maskers} present")

    all_run = run_with_bugs(set_id, bugs)
    _run_ok(rep, "all bugs", all_run)
    if fmt == "one_to_one":
        want_tests = {"tests." + b["test"] for b in bugs}
        got_tests = set(failing(all_run))
        rep.check(got_tests == want_tests, f"all bugs fail exactly the {len(want_tests)} bug tests"
                  + ("" if got_tests == want_tests else f" -> got {sorted(got_tests)}"))
        for bug in bugs:
            alone = set(failing(run_with_bugs(set_id, [bug])))
            rep.check(alone == {"tests." + bug["test"]}, f"{bug['id']} alone fails only {bug['test']}"
                      + ("" if alone == {"tests." + bug["test"]} else f" -> got {sorted(alone)}"))
            rest = set(failing(run_with_bugs(set_id, [b for b in bugs if b is not bug])))
            rep.check(rest == want_tests - {"tests." + bug["test"]},
                      f"fixing only {bug['id']} makes exactly {bug['test']} pass")
    want = sorted(spec.get("design", {}).get("all_bugs_failing_files")
                  or {b["test"].split(".")[0] for b in bugs if b.get("test")})
    got = failing_files(all_run)
    rep.check(got == want, f"all bugs fail {got} (designed {want})")
    observed["ALL"] = {"failing_files": got, "failing_tests": sorted(failing(all_run))}

    # ---- step 5: candidate + hint grep ---------------------------------------
    cand = set_dir(set_id) / "candidate"
    copy_repo(ref, cand)
    apply_bugs(cand, bugs)
    hits = grep_hints(cand)
    rep.check(not hits, "no hint words in candidate" + ("".join(f"\n       {h}" for h in hits) if hits else ""))
    marks = sum(p.read_text().count("# VERIFIED") for p in source_files(cand, spec["package"]))
    rep.check(1 <= marks <= 2, f"{marks} '# VERIFIED' markers")
    verified_syms = {v["symbol"] for v in spec.get("verified", [])}
    rep.check(not any(b["function"] in verified_syms or b["function"].split(".")[-1] in verified_syms
                      for b in bugs), "no bug inside a VERIFIED symbol")
    for v in spec.get("verified", []):
        text = (cand / v["file"]).read_text()
        name = v["symbol"].split(".")[-1]
        rep.check(re.search(rf"# VERIFIED\s*\n(?:\s*@.*\n)*\s*(async def|def|class) {re.escape(name)}\b", text)
                  is not None or v["symbol"] == "*", f"VERIFIED marker on {v['file']}:{v['symbol']}")

    (set_dir(set_id) / "interviewer" / "verification.json").write_text(json.dumps(observed, indent=2) + "\n")
    for cache in list(set_dir(set_id).rglob("__pycache__")) + list(set_dir(set_id).rglob(".pytest_cache")):
        shutil.rmtree(cache, ignore_errors=True)
    return rep


def sync_manifest(set_id: str, verified: bool) -> list[str]:
    with manifest_lock():
        return _sync_manifest(set_id, verified)


def _sync_manifest(set_id: str, verified: bool) -> list[str]:
    spec = load_spec(set_id)
    manifest = load_manifest()
    entry = next((s for s in manifest["sets"] if s["id"] == set_id), None)
    if entry is None:
        entry = {"id": set_id}
        manifest["sets"].append(entry)
    entry.update({
        "title": spec["title"],
        "domain": spec["domain"],
        "length": spec["length"],
        "difficulty": spec["difficulty"],
        "format": spec.get("format", "multi"),
        "bugs": [
            {k: b[k] for k in ("id", "type", "file", "function", "test", "old", "new", "masked_by", "visible_only_in")
             if k in b}
            for b in spec["bugs"]
        ],
        "status": "verified" if verified else "built",
    })
    if verified:
        entry["verified_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    # spec: no two sets may share domain + bug mix
    mix = (spec["domain"], tuple(sorted(b["type"] for b in spec["bugs"])))
    clashes = [s["id"] for s in manifest["sets"] if s["id"] != set_id and s.get("bugs")
               and (s["domain"], tuple(sorted(b["type"] for b in s["bugs"]))) == mix]
    if clashes:
        entry["status"] = "built"
    save_manifest(manifest)
    return clashes


def main(argv: list[str]) -> int:
    worst = 0
    for set_id in argv:
        rep = verify(set_id)
        clashes = sync_manifest(set_id, rep.ok())
        if clashes:
            rep.check(False, f"domain+bug-mix duplicates {clashes}")
        print(f"== {set_id}: {'VERIFIED' if rep.ok() else 'NOT VERIFIED'}")
        for line in rep.notes + rep.problems:
            print("  " + line)
        worst = worst or (0 if rep.ok() else 1)
    return worst


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
