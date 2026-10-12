#!/usr/bin/env python3
"""Judge: runs a problem's tests against your code (or the reference).

    python judge.py                 list problems and your progress
    python judge.py 09              submit workspace/09-*.py (run the tests)
    python judge.py 09 --run        just run your file (its __main__ block)
    python judge.py 09 --reveal     print the reference solution
    python judge.py 09 --reset      restore your file to the starter
    python judge.py 09 --tests      grade YOUR tests (workspace/09-*_test.py) against hidden bugs
    python judge.py 09 --run-tests  run your tests against your own solution
    python judge.py --verify [ids]  authoring check: reference passes, starter fails

serve.py imports the functions below for the web UI.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROBLEMS = ROOT / "problems"
WORKSPACE = ROOT / "workspace"
PROGRESS = ROOT / "progress.json"
TEST_TIMEOUT_S = 120
RUN_TIMEOUT_S = 30


# ------------------------------------------------------------------ problems


def _sort_key(meta: dict) -> tuple:
    pid = meta["id"]
    return (1, int(pid[1:]), "") if pid.upper().startswith("M") else (0, int(pid) if pid.isdigit() else 999, pid)


def all_problems() -> list[dict]:
    out = []
    for d in sorted(PROBLEMS.iterdir()) if PROBLEMS.exists() else []:
        meta_file = d / "meta.json"
        if d.is_dir() and meta_file.exists():
            meta = json.loads(meta_file.read_text())
            meta["dir"] = d.name
            meta.setdefault("parts", 1)
            meta.setdefault("tags", [])
            out.append(meta)
    return sorted(out, key=_sort_key)


def find(pid: str) -> dict:
    pid = pid.strip().lower()
    if pid.isdigit():
        pid = f"{int(pid):02d}"
    for meta in all_problems():
        if meta["id"].lower() == pid or meta["dir"].lower() == pid or meta["dir"].lower().startswith(pid + "-"):
            return meta
    raise LookupError(f"no problem {pid!r}; run `python judge.py` to list them")


def problem_dir(meta: dict) -> Path:
    return PROBLEMS / meta["dir"]


def workspace_file(meta: dict) -> Path:
    path = WORKSPACE / f"{meta['dir']}.py"
    if not path.exists():
        WORKSPACE.mkdir(exist_ok=True)
        shutil.copy(problem_dir(meta) / "starter.py", path)
    return path


def reset(meta: dict) -> None:
    shutil.copy(problem_dir(meta) / "starter.py", WORKSPACE / f"{meta['dir']}.py")


def statement(meta: dict) -> str:
    return (problem_dir(meta) / "problem.md").read_text()


def reference(meta: dict) -> str:
    return (problem_dir(meta) / "solution.py").read_text()


# ----------------------------------------------------------------- running


def _env(meta: dict, solution: Path) -> dict:
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join([str(ROOT), str(problem_dir(meta))])
    env["SOLUTION_PATH"] = str(solution)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env.pop("PYTEST_ADDOPTS", None)
    return env


def run_tests(meta: dict, solution: Path | None = None, test_file: Path | None = None,
              timeout: float = TEST_TIMEOUT_S) -> dict:
    """Run ``test_file`` (default: the problem's tests) against ``solution`` (default: your workspace file)."""
    solution = solution or workspace_file(meta)
    pdir = problem_dir(meta)
    test_file = test_file or pdir / "test_problem.py"
    with tempfile.TemporaryDirectory(prefix="judge-") as tmp:
        results_path = Path(tmp) / "results.json"
        env = _env(meta, solution)
        env["RESULTS_PATH"] = str(results_path)
        cmd = [sys.executable, "-m", "pytest", str(test_file), "-q", "--no-header",
               "-p", "no:cacheprovider", "-p", "kit.pytest_plugin", "--rootdir", str(pdir),
               "--import-mode=importlib", "-o", "console_output_style=classic", "-p", "no:warnings"]
        started = time.time()
        try:
            proc = subprocess.run(cmd, cwd=tmp, env=env, capture_output=True, text=True, timeout=timeout)
            timed_out = False
        except subprocess.TimeoutExpired as exc:
            proc = None
            timed_out = True
            partial = (exc.stdout or b"").decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        elapsed = round(time.time() - started, 2)
        data = json.loads(results_path.read_text()) if results_path.exists() else {"cases": [], "collect_errors": []}

    skipped = sum(1 for c in data["cases"] if c["outcome"] == "skipped")
    cases = [c for c in data["cases"] if c["outcome"] != "skipped"]
    passed = sum(1 for c in cases if c["outcome"] == "passed")
    error = None
    if timed_out:
        error = f"Time limit exceeded: the tests did not finish within {timeout:g}s (infinite loop? real sleep?).\n{partial[-2000:]}"
    elif data["collect_errors"]:
        what = "Your file" if test_file.name == "test_problem.py" else "Your test file"
        error = f"{what} could not be imported:\n\n" + "\n".join(data["collect_errors"])
    elif not cases and proc is not None:
        error = (proc.stdout + proc.stderr)[-6000:] or "no tests ran"

    parts = meta.get("parts", 1)
    part_summary = []
    for n in range(1, parts + 1):
        pc = [c for c in cases if c["part"] == n]
        part_summary.append({"part": n, "passed": sum(c["outcome"] == "passed" for c in pc), "total": len(pc)})

    return {
        "id": meta["id"],
        "passed": passed,
        "total": len(cases),
        "skipped": skipped,
        "accepted": bool(error is None and cases and passed == len(cases)),
        "cases": cases,
        "parts": part_summary,
        "error": error,
        "elapsed": elapsed,
    }


# --------------------------------------------------------------- tests mode
#
# You write tests in workspace/<dir>_test.py. Submitting runs them against the
# reference solution (they must all pass: a test that fails on correct code is
# a wrong test) and against each "mutant": the reference with a realistic bug
# planted (problems/<dir>/mutants.json). A mutant is caught when at least one
# of your tests fails on it.

MUTANT_TIMEOUT_S = 10


def has_tests_mode(meta: dict) -> bool:
    return meta.get("tests_mode", True) and (problem_dir(meta) / "mutants.json").exists()


def tests_file(meta: dict) -> Path:
    path = WORKSPACE / f"{meta['dir']}_test.py"
    if not path.exists():
        WORKSPACE.mkdir(exist_ok=True)
        path.write_text(tests_starter(meta))
    return path


def reset_tests(meta: dict) -> None:
    (WORKSPACE / f"{meta['dir']}_test.py").write_text(tests_starter(meta))


def tests_starter(meta: dict) -> str:
    custom = problem_dir(meta) / "tests_starter.py"
    if custom.exists():
        return custom.read_text()
    return f"# Tests for {meta['id']}. {meta['title']}. Fixtures: sol (your module), clock, tmp_path, monkeypatch\n"


def mutants(meta: dict) -> list[dict]:
    path = problem_dir(meta) / "mutants.json"
    return json.loads(path.read_text()) if path.exists() else []


def mutant_source(meta: dict, mutant: dict) -> str:
    """Apply a mutant's edits to the reference. Each `find` must occur exactly once."""
    src = reference(meta)
    for edit in mutant["edits"]:
        count = src.count(edit["find"])
        if count != 1:
            raise ValueError(f"mutant {mutant['id']}: `find` occurs {count} times (must be exactly once): {edit['find'][:80]!r}")
        src = src.replace(edit["find"], edit["replace"])
    return src


def _failed_names(result: dict) -> list[str]:
    return [c["doc"] or c["name"] for c in result["cases"] if c["outcome"] != "passed"]


def grade_tests(meta: dict, test_file: Path | None = None, include_mine: bool = True) -> dict:
    """Run a test suite against the reference, (optionally) your solution, and every mutant."""
    from concurrent.futures import ThreadPoolExecutor

    test_file = test_file or tests_file(meta)
    pdir = problem_dir(meta)
    ms = mutants(meta)
    started = time.time()
    with tempfile.TemporaryDirectory(prefix="mutants-") as tmp:
        paths = []
        for m in ms:
            p = Path(tmp) / f"{m['id']}.py"
            p.write_text(mutant_source(meta, m))
            paths.append(p)
        with ThreadPoolExecutor(max_workers=4) as pool:
            ref_f = pool.submit(run_tests, meta, pdir / "solution.py", test_file)
            mine_f = pool.submit(run_tests, meta, workspace_file(meta), test_file) if include_mine else None
            mut_fs = [pool.submit(run_tests, meta, p, test_file, MUTANT_TIMEOUT_S) for p in paths]
            ref = ref_f.result()
            mine = mine_f.result() if mine_f else None
            mut_results = [f.result() for f in mut_fs]

    valid = bool(ref["accepted"])
    rows = []
    for m, r in zip(ms, mut_results):
        timed_out = bool(r["error"] and r["error"].startswith("Time limit"))
        caught = valid and (timed_out or r["passed"] < r["total"] or bool(r["error"]))
        rows.append({"id": m["id"], "bug": m["bug"], "caught": caught,
                     "caught_by": (["(your tests hung: the bug causes an infinite loop)"] if timed_out else _failed_names(r))
                     if caught else []})
    caught = sum(r["caught"] for r in rows)
    return {
        "id": meta["id"],
        "kind": "tests",
        "valid": valid,
        "empty": ref["total"] == 0 and not (ref["error"] or "").startswith(("Your test file", "Time limit")),
        "n_tests": ref["total"],
        "reference": ref,
        "mine": mine,
        "mutants": rows,
        "caught": caught,
        "total_mutants": len(rows),
        "accepted": valid and ref["total"] > 0 and caught == len(rows),
        "elapsed": round(time.time() - started, 2),
    }


def record_tests(result: dict) -> dict:
    progress = load_progress()
    entry = progress.get(result["id"], {"submissions": 0, "best": 0, "solved": False, "parts_passed": []})
    t = entry.get("tests", {"submissions": 0, "best_caught": 0, "solved": False})
    t["submissions"] += 1
    if result["valid"]:
        t["best_caught"] = max(t["best_caught"], result["caught"])
    t["total"] = result["total_mutants"]
    t["solved"] = t["solved"] or bool(result["accepted"])
    t["last"] = time.strftime("%Y-%m-%d %H:%M")
    entry["tests"] = t
    progress[result["id"]] = entry
    tmp = PROGRESS.with_suffix(".tmp")
    tmp.write_text(json.dumps(progress, indent=2))
    os.replace(tmp, PROGRESS)
    return entry


def run_code(meta: dict, solution: Path | None = None) -> dict:
    """Run the file itself (its ``if __name__ == "__main__":`` block)."""
    solution = solution or workspace_file(meta)
    with tempfile.TemporaryDirectory(prefix="run-") as tmp:
        started = time.time()
        try:
            proc = subprocess.run([sys.executable, str(solution)], cwd=tmp, env=_env(meta, solution),
                                  capture_output=True, text=True, timeout=RUN_TIMEOUT_S)
            return {"stdout": proc.stdout[-20000:], "stderr": proc.stderr[-20000:], "exit_code": proc.returncode,
                    "elapsed": round(time.time() - started, 2)}
        except subprocess.TimeoutExpired as exc:
            out = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
            return {"stdout": out[-20000:], "stderr": f"Time limit exceeded ({RUN_TIMEOUT_S}s)", "exit_code": -1,
                    "elapsed": RUN_TIMEOUT_S}


# ---------------------------------------------------------------- progress


def load_progress() -> dict:
    try:
        return json.loads(PROGRESS.read_text())
    except (OSError, ValueError):
        return {}


def record(result: dict) -> dict:
    progress = load_progress()
    entry = progress.get(result["id"], {"submissions": 0, "best": 0, "solved": False, "parts_passed": []})
    entry["submissions"] += 1
    entry["best"] = max(entry["best"], result["passed"])
    entry["total"] = result["total"]
    entry["solved"] = entry["solved"] or bool(result["accepted"])
    passed_parts = {p["part"] for p in result["parts"] if p["total"] and p["passed"] == p["total"]}
    entry["parts_passed"] = sorted(set(entry["parts_passed"]) | passed_parts)
    entry["last"] = time.strftime("%Y-%m-%d %H:%M")
    progress[result["id"]] = entry
    tmp = PROGRESS.with_suffix(".tmp")
    tmp.write_text(json.dumps(progress, indent=2))
    os.replace(tmp, PROGRESS)
    return entry


# --------------------------------------------------------------------- CLI

GREEN, RED, YELLOW, DIM, BOLD, RESET = "\033[32m", "\033[31m", "\033[33m", "\033[2m", "\033[1m", "\033[0m"


def _print_compare(cmp: dict | None) -> None:
    if not cmp:
        return
    for d in cmp.get("diffs") or []:
        print(f"      {YELLOW}• {d}{RESET}")
    if not cmp.get("diffs"):
        for label, key in (("expected", "expected"), ("got     ", "actual")):
            text = cmp[key] if len(cmp[key]) < 300 else cmp[key][:300] + " ..."
            print(f"      {DIM}{label}:{RESET} {text.replace(chr(10), chr(10) + ' ' * 16)}")


def _print_result(result: dict, verbose: bool) -> None:
    for case in result["cases"]:
        ok = case["outcome"] == "passed"
        mark = f"{GREEN}✔{RESET}" if ok else f"{RED}✘{RESET}"
        label = case["doc"] or case["name"]
        print(f"  {mark} {label}")
        if not ok:
            print(f"      {RED}{case['short'].splitlines()[0] if case['short'] else ''}{RESET}")
            _print_compare(case.get("compare"))
            if verbose:
                print("\n".join("      " + line for line in case["long"].splitlines()[-40:]))
    if result["error"]:
        print(f"\n{RED}{result['error']}{RESET}")
    colour = GREEN if result["accepted"] else RED
    verdict = "All checks pass" if result["accepted"] else "Checks failing" if result["cases"] else "Could not run"
    print(f"\n{BOLD}{colour}{verdict}{RESET}  {result['passed']}/{result['total']} passed  {DIM}({result['elapsed']}s){RESET}")
    if len(result["parts"]) > 1:
        print("  " + "   ".join(f"part {p['part']}: {p['passed']}/{p['total']}" for p in result["parts"]))


def _list() -> None:
    progress = load_progress()
    group = None
    solved = 0
    problems = all_problems()
    for meta in problems:
        if meta["group"] != group:
            group = meta["group"]
            print(f"\n{BOLD}{group}{RESET}")
        entry = progress.get(meta["id"])
        if entry and entry["solved"]:
            solved += 1
            mark = f"{GREEN}✔{RESET}"
        elif entry:
            mark = f"{YELLOW}…{RESET}"
        else:
            mark = " "
        star = "★" if meta.get("daily") else " "
        print(f"  {mark} {meta['id']:>3} {star} {meta['title']:<46} {DIM}{meta['level']:<6} ~{meta.get('minutes', '?')}m{RESET}")
    print(f"\n{solved}/{len(problems)} solved.  ★ = daily practice.  Web UI: python serve.py")


def _verify(ids: list[str]) -> int:
    metas = [find(i) for i in ids] if ids else all_problems()
    bad = 0
    for meta in metas:
        pdir = problem_dir(meta)
        missing = [f for f in ("meta.json", "problem.md", "starter.py", "solution.py", "test_problem.py")
                   if not (pdir / f).exists()]
        if missing:
            print(f"{RED}✘ {meta['dir']}: missing {missing}{RESET}")
            bad += 1
            continue
        ref = run_tests(meta, pdir / "solution.py")
        start = run_tests(meta, pdir / "starter.py")
        parts_ok = all(p["total"] > 0 for p in ref["parts"])
        ok = ref["accepted"] and start["passed"] < start["total"] and parts_ok
        bad += not ok
        mark = f"{GREEN}✔{RESET}" if ok else f"{RED}✘{RESET}"
        print(f"{mark} {meta['dir']:<40} reference {ref['passed']}/{ref['total']}  starter {start['passed']}/{start['total']}"
              f"  {DIM}{ref['elapsed']}s{RESET}")
        if not ref["accepted"]:
            for c in ref["cases"]:
                if c["outcome"] != "passed":
                    print(f"    {RED}{c['name']}: {c['short']}{RESET}")
            if ref["error"]:
                print(f"    {RED}{ref['error'][:3000]}{RESET}")
        if not parts_ok:
            print(f"    {RED}a part has no tests: {ref['parts']}{RESET}")
        if ok and meta.get("tests_mode", True):
            bad += not _verify_mutants(meta)
    print(f"\n{len(metas) - bad}/{len(metas)} problems verified")
    return 1 if bad else 0


def _verify_mutants(meta: dict) -> bool:
    """Every mutant applies cleanly, changes the code, and is caught by the official tests."""
    if not (problem_dir(meta) / "mutants.json").exists():
        print(f"    {RED}missing mutants.json (or set \"tests_mode\": false in meta.json){RESET}")
        return False
    ms = mutants(meta)
    problems = []
    if len(ms) < 3:
        problems.append(f"only {len(ms)} mutants (need at least 3)")
    if len({m["id"] for m in ms}) != len(ms):
        problems.append("duplicate mutant ids")
    sources = set()
    for m in ms:
        if not m.get("bug"):
            problems.append(f"{m.get('id')}: missing `bug` description")
        try:
            src = mutant_source(meta, m)
        except (ValueError, KeyError) as exc:
            problems.append(str(exc))
            continue
        if src == reference(meta) or src in sources:
            problems.append(f"{m['id']}: identical to the reference or another mutant")
        sources.add(src)
    if problems:
        for msg in problems:
            print(f"    {RED}{msg}{RESET}")
        return False
    graded = grade_tests(meta, problem_dir(meta) / "test_problem.py", include_mine=False)
    starter_suite = Path(tempfile.mkdtemp(prefix="starter-tests-")) / "starter_test.py"
    starter_suite.write_text(tests_starter(meta))
    sr = run_tests(meta, problem_dir(meta) / "solution.py", starter_suite)
    starter_ok = sr["accepted"] or (sr["total"] == 0 and not (sr["error"] or "").startswith("Your test file"))
    shutil.rmtree(starter_suite.parent, ignore_errors=True)
    missed = [m for m in graded["mutants"] if not m["caught"]]
    ok = graded["valid"] and not missed and starter_ok
    mark = f"{GREEN}✔{RESET}" if ok else f"{RED}✘{RESET}"
    print(f"    {mark} mutants: official tests catch {graded['caught']}/{graded['total_mutants']}"
          f"{'' if starter_ok else f'  {RED}(tests starter does not pass on the reference){RESET}'}  {DIM}{graded['elapsed']}s{RESET}")
    for m in missed:
        print(f"      {RED}not caught {m['id']}: {m['bug']}{RESET}")
    return ok


def _print_tests_result(result: dict, verbose: bool) -> None:
    ref = result["reference"]
    if result.get("empty"):
        print(f"{YELLOW}No tests yet{RESET}: add test_* functions that take `sol`.")
        return
    if not result["valid"]:
        print(f"{RED}{BOLD}Invalid test suite{RESET}: your tests must all pass on the correct solution.")
        for c in ref["cases"]:
            if c["outcome"] != "passed":
                print(f"  {RED}✘ {c['doc'] or c['name']}{RESET}\n      {c['short']}")
        if ref["error"]:
            print(f"{RED}{ref['error']}{RESET}")
        return
    mine = result.get("mine")
    if mine is not None:
        status = f"{GREEN}all pass{RESET}" if mine["accepted"] else f"{YELLOW}{mine['passed']}/{mine['total']} pass{RESET}"
        print(f"  on your solution: {status}")
    print(f"  {result['n_tests']} tests, all passing on the reference solution\n")
    for m in result["mutants"]:
        if m["caught"]:
            print(f"  {GREEN}✔ caught{RESET} {m['bug']}  {DIM}by: {'; '.join(m['caught_by'][:2])}{RESET}")
        else:
            print(f"  {RED}✘ missed{RESET} {m['bug'] if verbose else '(run with -v to see the bug)'}")
    colour = GREEN if result["accepted"] else YELLOW
    print(f"\n{BOLD}{colour}{result['caught']}/{result['total_mutants']} bugs caught{RESET}  {DIM}({result['elapsed']}s){RESET}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("problem", nargs="?", help="problem id, e.g. 09 or M1")
    ap.add_argument("--run", action="store_true", help="run your file instead of the tests")
    ap.add_argument("--reveal", action="store_true", help="print the reference solution")
    ap.add_argument("--reset", action="store_true", help="restore your file to the starter code")
    ap.add_argument("--verify", nargs="*", metavar="ID", help="check reference passes and starter fails")
    ap.add_argument("--tests", action="store_true", help="grade YOUR tests (workspace/<dir>_test.py) against hidden buggy versions")
    ap.add_argument("--run-tests", action="store_true", help="run your tests against your own solution")
    ap.add_argument("--reset-tests", action="store_true", help="restore your test file to the template")
    ap.add_argument("-v", "--verbose", action="store_true", help="show full tracebacks / missed bugs")
    args = ap.parse_args(argv)

    if args.verify is not None:
        return _verify(args.verify)
    if not args.problem:
        _list()
        return 0
    try:
        meta = find(args.problem)
    except LookupError as exc:
        print(exc, file=sys.stderr)
        return 2
    if args.reset:
        reset(meta)
        print(f"reset {workspace_file(meta)}")
        return 0
    if args.reveal:
        print(reference(meta))
        return 0
    if args.reset_tests:
        reset_tests(meta)
        print(f"reset {tests_file(meta)}")
        return 0
    if args.tests or args.run_tests:
        if not has_tests_mode(meta):
            print("this problem has no tests mode", file=sys.stderr)
            return 2
        tf = tests_file(meta)
        print(f"{BOLD}{meta['id']}. {meta['title']}: your tests{RESET}  {DIM}{tf.relative_to(ROOT)}{RESET}\n")
        if args.run_tests:
            result = run_tests(meta, workspace_file(meta), tf)
            _print_result(result, args.verbose)
            return 0 if result["accepted"] else 1
        result = grade_tests(meta)
        record_tests(result)
        _print_tests_result(result, args.verbose)
        return 0 if result["accepted"] else 1
    path = workspace_file(meta)
    if args.run:
        out = run_code(meta)
        sys.stdout.write(out["stdout"])
        sys.stderr.write(out["stderr"])
        return out["exit_code"]
    print(f"{BOLD}{meta['id']}. {meta['title']}{RESET}  {DIM}{path.relative_to(ROOT)}{RESET}\n")
    result = run_tests(meta)
    record(result)
    _print_result(result, args.verbose)
    return 0 if result["accepted"] else 1


if __name__ == "__main__":
    sys.exit(main())
