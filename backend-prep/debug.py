#!/usr/bin/env python3
"""Debug practice: the Scale-style "Debugging Practical" round on the sets in
../scale-debug-sets.

You never edit the original sets. Opening a set copies its candidate/ repo to
debug-workspace/<set>/; you fix bugs there. Tests always run against the
original tests/, data/ and README.md (copied over your workspace in a temp
dir), so editing them can't make tests pass.

    python debug.py                  list sets + progress
    python debug.py set-007          run all tests on your workspace copy
    python debug.py set-007 --test 1 run only Test 1
    python debug.py set-007 --main   run main.py
    python debug.py set-007 --reset  start over from the original buggy repo
    python debug.py set-007 --reveal print the answer key (marks the set revealed)

serve.py imports the functions below for the web UI.
"""

from __future__ import annotations

import argparse
import ast
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
SETS = Path(os.environ.get("DEBUG_SETS_DIR", ROOT.parent / "scale-debug-sets")).resolve()
WORKSPACE = ROOT / "debug-workspace"
PROGRESS = ROOT / "debug_progress.json"
LOCKED_DIRS = ("tests", "data")
LOCKED_FILES = ("README.md",)
SKIP = {"__pycache__", ".pytest_cache", ".DS_Store", ".built-from"}
TEST_TIMEOUT_S = 60
RUN_TIMEOUT_S = 30


# --------------------------------------------------------------------- sets


def _manifest() -> list[dict]:
    try:
        return json.loads((SETS / "manifest.json").read_text())["sets"]
    except (OSError, ValueError, KeyError):
        return []


def bugs_doc(sid: str) -> dict:
    return json.loads((SETS / sid / "interviewer" / "bugs.json").read_text())


def all_sets() -> list[dict]:
    progress = load_progress()
    out = []
    for entry in _manifest():
        sid = entry["id"]
        if not (SETS / sid / "interviewer" / "reference").is_dir():
            continue
        try:
            doc = bugs_doc(sid)
        except (OSError, ValueError):
            doc = {}
        out.append({
            "id": sid,
            "title": doc.get("title") or entry.get("title", sid),
            "domain": entry.get("domain", ""),
            "length": entry.get("length", ""),
            "difficulty": entry.get("difficulty", ""),
            "minutes": 30 if entry.get("length") == "MINI" else 60,
            "n_bugs": len(entry.get("bugs", [])),
            "scenario": doc.get("scenario", ""),
            "progress": progress.get(sid),
        })
    return out


def find(sid: str) -> str:
    sid = sid.strip().lower()
    if sid.isdigit():
        sid = f"set-{int(sid):03d}"
    if not sid.startswith("set-"):
        sid = "set-" + sid
    if not (SETS / sid / "interviewer" / "reference").is_dir():
        raise LookupError(f"no debug set {sid!r} in {SETS}")
    return sid


PRISTINE = ROOT / ".debug-pristine"


def original(sid: str) -> Path:
    """The buggy repo exactly as the set defines it: interviewer/reference/ plus every bug's
    edits (old -> new, including `extra` edits), built the same way the set tooling builds
    candidate/. Built here rather than copied from candidate/, so fixes you made directly in
    candidate/ during earlier practice never leak in. Cached; rebuilt when bugs.json changes."""
    dst = PRISTINE / sid
    spec_file = SETS / sid / "interviewer" / "bugs.json"
    stamp = dst / ".built-from"
    want = str(spec_file.stat().st_mtime_ns)
    if stamp.exists() and stamp.read_text() == want:
        return dst
    tmp = PRISTINE / f".{sid}.building"
    shutil.rmtree(tmp, ignore_errors=True)
    PRISTINE.mkdir(exist_ok=True)
    _copy_tree(SETS / sid / "interviewer" / "reference", tmp)
    for bug in bugs_doc(sid)["bugs"]:
        edits = [{"file": bug["file"], "old": bug["old"], "new": bug["new"]}]
        edits += [{"file": e.get("file", bug["file"]), "old": e["old"], "new": e["new"]} for e in bug.get("extra", [])]
        for e in edits:
            path = tmp / e["file"]
            text = path.read_text()
            if text.count(e["old"]) != 1:
                raise ValueError(f"{sid} {bug['id']}: cannot apply edit to {e['file']}")
            path.write_text(text.replace(e["old"], e["new"], 1))
    (tmp / ".built-from").write_text(want)
    shutil.rmtree(dst, ignore_errors=True)
    tmp.rename(dst)
    return dst


def workspace(sid: str) -> Path:
    path = WORKSPACE / sid
    if not path.exists():
        WORKSPACE.mkdir(exist_ok=True)
        _copy_tree(original(sid), path)
    return path


def _copy_tree(src: Path, dst: Path) -> None:
    shutil.copytree(src, dst, ignore=lambda d, names: [n for n in names if n in SKIP or n.endswith(".pyc")])


def reset(sid: str) -> None:
    shutil.rmtree(WORKSPACE / sid, ignore_errors=True)
    workspace(sid)


def is_locked(rel: str) -> bool:
    parts = Path(rel).parts
    return bool(parts) and (parts[0] in LOCKED_DIRS or rel in LOCKED_FILES)


def files(sid: str) -> list[dict]:
    root = workspace(sid)
    out = []
    for path in sorted(root.rglob("*")):
        if path.is_dir() or any(p in SKIP for p in path.parts) or path.suffix == ".pyc":
            continue
        rel = path.relative_to(root).as_posix()
        out.append({"path": rel, "locked": is_locked(rel), "verified": path.suffix == ".py" and "# VERIFIED" in _read(path)})
    # README first, then code, then tests, then data
    order = lambda f: (0 if f["path"] == "README.md" else 2 if f["path"].startswith("tests/") else 3 if f["path"].startswith("data/") else 1, f["path"])
    return sorted(out, key=order)


def _safe(root: Path, rel: str) -> Path:
    path = (root / rel).resolve()
    if root.resolve() not in path.parents:
        raise ValueError(f"bad path {rel!r}")
    return path


def _read(path: Path) -> str:
    try:
        return path.read_text()
    except UnicodeDecodeError:
        return path.read_bytes().decode("utf-8", "replace")


def read_file(sid: str, rel: str) -> str:
    return _read(_safe(workspace(sid), rel))


def write_file(sid: str, rel: str, content: str) -> None:
    if is_locked(rel):
        raise PermissionError(f"{rel} is read-only (tests, data and the README spec can't be changed)")
    path = _safe(workspace(sid), rel)
    if not path.exists():
        raise FileNotFoundError(rel)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(content)
    os.replace(tmp, path)


def notes_path(sid: str) -> Path:
    return WORKSPACE / f"{sid}.notes.md"


NOTES_TEMPLATE = """## Bug 1
- where (file / function):
- symptom (which test, what was wrong):
- root cause:
- fix:

"""


def read_notes(sid: str) -> str:
    p = notes_path(sid)
    return p.read_text() if p.exists() else NOTES_TEMPLATE


def write_notes(sid: str, text: str) -> None:
    WORKSPACE.mkdir(exist_ok=True)
    notes_path(sid).write_text(text)


def test_files(sid: str) -> list[dict]:
    out = []
    for p in sorted((original(sid) / "tests").glob("test_*.py")):
        m = re.match(r"test_(\d+)_?(.*)", p.stem)
        n = int(m.group(1)) if m else len(out) + 1
        label = (m.group(2) if m else p.stem).replace("_", " ")
        out.append({"n": n, "file": p.name, "label": f"Test {n}: {label}".strip()})
    return out


# ---------------------------------------------------------------- integrity


def _changed_locked(sid: str) -> list[str]:
    ws, orig = workspace(sid), original(sid)
    changed = []
    for rel in [*LOCKED_FILES, *[p.relative_to(orig).as_posix() for d in LOCKED_DIRS
                                for p in (orig / d).rglob("*") if p.is_file() and not any(s in SKIP for s in p.parts)]]:
        a, b = orig / rel, ws / rel
        if not b.exists() or a.read_bytes() != b.read_bytes():
            changed.append(rel)
    return changed


def _verified_nodes(src: str) -> dict[str, str]:
    """{qualified name: ast dump} for every def/class right after a '# VERIFIED' line."""
    lines = src.splitlines()
    marks = {i + 2 for i, line in enumerate(lines) if line.strip() == "# VERIFIED"}  # 1-based line after marker
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return {}
    found: dict[str, str] = {}

    def walk(node, prefix=""):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                start = min([child.lineno] + [d.lineno for d in child.decorator_list])
                name = prefix + child.name
                if start in marks:
                    found[name] = ast.dump(child)
                walk(child, name + ".")

    walk(tree)
    return found


def verified_changes(sid: str) -> list[str]:
    """VERIFIED functions/classes whose code you changed (comments/formatting don't count)."""
    ws, orig = workspace(sid), original(sid)
    changed = []
    for path in orig.rglob("*.py"):
        if any(s in SKIP for s in path.parts):
            continue
        src = _read(path)
        if "# VERIFIED" not in src:
            continue
        rel = path.relative_to(orig).as_posix()
        before = _verified_nodes(src)
        mine = ws / rel
        try:
            after_tree = ast.parse(_read(mine)) if mine.exists() else None
        except SyntaxError:
            after_tree = None
        after: dict[str, str] = {}
        if after_tree is not None:
            def walk(node, prefix=""):
                for child in ast.iter_child_nodes(node):
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                        after[prefix + child.name] = ast.dump(child)
                        walk(child, prefix + child.name + ".")
            walk(after_tree)
        for name, dump in before.items():
            if after.get(name) != dump:
                changed.append(f"{rel}: {name}")
    return changed


# ------------------------------------------------------------------ running


def _staged_copy(sid: str, tmp: Path) -> Path:
    """Your workspace with the original tests/, data/ and README.md put back."""
    dst = tmp / sid
    _copy_tree(workspace(sid), dst)
    for d in LOCKED_DIRS:
        shutil.rmtree(dst / d, ignore_errors=True)
        if (original(sid) / d).exists():
            _copy_tree(original(sid) / d, dst / d)
    for f in LOCKED_FILES:
        if (original(sid) / f).exists():
            shutil.copy(original(sid) / f, dst / f)
    return dst


def _env(code_root: Path, results: Path | None = None) -> dict:
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join([str(code_root), str(ROOT)])
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env.pop("PYTEST_ADDOPTS", None)
    if results:
        env["RESULTS_PATH"] = str(results)
    return env


def run_tests(sid: str, test: int | None = None) -> dict:
    tfiles = test_files(sid)
    targets = [t for t in tfiles if test is None or t["n"] == test]
    if not targets:
        raise LookupError(f"{sid} has no Test {test}")
    started = time.time()
    with tempfile.TemporaryDirectory(prefix="debug-") as tmp:
        tmp = Path(tmp).resolve()  # macOS: /var -> /private/var, or pytest node ids lose the file
        code = _staged_copy(sid, tmp)
        results = tmp / "results.json"
        cmd = [sys.executable, "-m", "pytest", *[f"tests/{t['file']}" for t in targets], "-q", "--no-header",
               "-p", "no:cacheprovider", "-p", "kit.pytest_plugin", "-p", "no:warnings", "--rootdir", str(code)]
        error = None
        try:
            proc = subprocess.run(cmd, cwd=code, env=_env(code, results), capture_output=True, text=True,
                                  timeout=TEST_TIMEOUT_S)
        except subprocess.TimeoutExpired:
            proc, error = None, f"Timed out after {TEST_TIMEOUT_S}s (infinite loop? real sleep?)"
        data = json.loads(results.read_text()) if results.exists() else {"cases": [], "collect_errors": []}
    cases = [c for c in data["cases"] if c["outcome"] != "skipped"]
    if not error and data["collect_errors"]:
        error = "The tests could not import your code:\n\n" + "\n".join(data["collect_errors"])
    elif not error and not cases and proc is not None:
        error = (proc.stdout + proc.stderr)[-6000:] or "no tests ran"
    by_file = []
    for t in targets:
        tc = [c for c in cases if c["file"] == t["file"]]
        by_file.append({**t, "passed": sum(c["outcome"] == "passed" for c in tc), "total": len(tc)})
    passed = sum(c["outcome"] == "passed" for c in cases)
    tampered = _changed_locked(sid)
    vchanged = verified_changes(sid)
    return {
        "id": sid,
        "scope": "all" if test is None else f"Test {test}",
        "passed": passed,
        "total": len(cases),
        "all_pass": error is None and bool(cases) and passed == len(cases),
        "tests": by_file,
        "cases": cases,
        "error": error,
        "tampered": tampered,
        "verified_changed": vchanged,
        "elapsed": round(time.time() - started, 2),
    }


def run_main(sid: str) -> dict:
    with tempfile.TemporaryDirectory(prefix="debug-run-") as tmp:
        code = _staged_copy(sid, Path(tmp).resolve())
        started = time.time()
        try:
            proc = subprocess.run([sys.executable, "main.py"], cwd=code, env=_env(code), capture_output=True,
                                  text=True, timeout=RUN_TIMEOUT_S)
            return {"stdout": proc.stdout[-30000:], "stderr": proc.stderr[-20000:], "exit_code": proc.returncode,
                    "elapsed": round(time.time() - started, 2)}
        except subprocess.TimeoutExpired:
            return {"stdout": "", "stderr": f"Timed out after {RUN_TIMEOUT_S}s", "exit_code": -1, "elapsed": RUN_TIMEOUT_S}


def diff(sid: str) -> str:
    """Unified diff of your changes against the original buggy repo (code files only)."""
    import difflib

    ws, orig = workspace(sid), original(sid)
    chunks = []
    for f in files(sid):
        if f["locked"]:
            continue
        a, b = orig / f["path"], ws / f["path"]
        before = _read(a).splitlines(keepends=True) if a.exists() else []
        after = _read(b).splitlines(keepends=True)
        chunks.extend(difflib.unified_diff(before, after, f"original/{f['path']}", f"yours/{f['path']}"))
    return "".join(chunks)


# ----------------------------------------------------------- hints & answers


def _norm(s: str) -> str:
    """Drop trailing whitespace and blank lines; keep indentation (some bugs ARE indentation)."""
    return "\n".join(line.rstrip() for line in s.splitlines() if line.strip())


def _still_buggy(sid: str, bug: dict) -> bool:
    """Is the planted bug still in your code?

    Fixed means the buggy snippet occurs fewer times than in the original, or the
    correct snippet occurs more times (handles a fix that contains the buggy text, e.g. a
    removed `await`). Trailing whitespace and blank lines are ignored; indentation is not.
    """
    mine_path, orig_path = workspace(sid) / bug["file"], original(sid) / bug["file"]
    if not mine_path.exists():
        return False
    mine, orig = _norm(_read(mine_path)), _norm(_read(orig_path))
    buggy, fixed = _norm(bug["new"]), _norm(bug["old"])
    if buggy and mine.count(buggy) < orig.count(buggy):
        return False
    if fixed and mine.count(fixed) > orig.count(fixed):
        return False
    return True


def hint(sid: str) -> dict:
    """Next hint for the first bug whose planted code is still present. Hints get more specific."""
    doc = bugs_doc(sid)
    progress = load_progress()
    entry = progress.setdefault(sid, _new_entry())
    levels: dict = entry.setdefault("hint_levels", {})
    for i, bug in enumerate(doc["bugs"], 1):
        if not _still_buggy(sid, bug):
            continue
        hints = bug.get("hints") or []
        level = levels.get(bug["id"], 0)
        if level >= len(hints):
            text, level_out = "No more hints for this one. Reveal the answer key if you're stuck.", level
        else:
            text, level_out = hints[level], level + 1
            levels[bug["id"]] = level_out
            entry["hints_used"] = entry.get("hints_used", 0) + 1
        _save_progress(progress)
        return {"bug": f"Bug {i} of {len(doc['bugs'])}", "level": level_out, "of": len(hints), "hint": text}
    return {"bug": None, "hint": "Every planted bug's original line is gone from your code. If tests still fail, "
                                 "re-read the failing assertion: a fix may be incomplete or a new bug introduced."}


def context_questions(sid: str) -> list[dict]:
    return bugs_doc(sid).get("context_qa", [])


def answer_key(sid: str) -> dict:
    """Everything the interviewer has. Marks the set as revealed."""
    doc = bugs_doc(sid)
    bugs = []
    for i, b in enumerate(doc["bugs"], 1):
        bugs.append({
            "n": i, "id": b["id"], "title": b.get("title", ""), "type": b.get("type", ""),
            "file": b["file"], "function": b.get("function", ""), "test": b.get("test"),
            "buggy": b["new"], "fixed": b["old"], "symptom": b.get("symptom", ""), "why": b.get("why", ""),
            "unblocks": b.get("unblocks", ""), "probes": b.get("probes", []), "masked_by": b.get("masked_by", []),
            "you_fixed": not _still_buggy(sid, b),
        })
    progress = load_progress()
    entry = progress.setdefault(sid, _new_entry())
    if not entry.get("revealed"):
        entry["revealed"] = time.strftime("%Y-%m-%d %H:%M")
        entry["found_at_reveal"] = {b["id"]: b["you_fixed"] for b in bugs}
        entry["types"] = {b["id"]: b["type"] for b in bugs}
        _save_progress(progress)
    return {"id": sid, "title": doc.get("title"), "scenario": doc.get("scenario"), "bugs": bugs,
            "verified": doc.get("verified", []), "found": sum(b["you_fixed"] for b in bugs)}


# ----------------------------------------------------------------- progress


def _new_entry() -> dict:
    return {"runs": 0, "best_passed": 0, "total": 0, "solved": False, "hints_used": 0}


def load_progress() -> dict:
    try:
        return json.loads(PROGRESS.read_text())
    except (OSError, ValueError):
        return {}


def _save_progress(progress: dict) -> None:
    tmp = PROGRESS.with_suffix(".tmp")
    tmp.write_text(json.dumps(progress, indent=2))
    os.replace(tmp, PROGRESS)


def record(result: dict, elapsed_s: float | None = None) -> dict:
    progress = load_progress()
    entry = progress.setdefault(result["id"], _new_entry())
    entry["runs"] += 1
    entry.setdefault("started", time.strftime("%Y-%m-%d %H:%M"))
    if result["scope"] == "all":
        entry["best_passed"] = max(entry["best_passed"], result["passed"])
        entry["total"] = result["total"]
        clean = not result["tampered"] and not result["verified_changed"]
        if result["all_pass"] and clean and not entry["solved"]:
            entry["solved"] = True
            entry["solved_at"] = time.strftime("%Y-%m-%d %H:%M")
            entry["solved_before_reveal"] = not entry.get("revealed")
            if elapsed_s is not None:
                entry["time_s"] = round(elapsed_s)
    _save_progress(progress)
    return entry


def weak_spots() -> list[dict]:
    """Bug types you missed vs found, over sets whose answer key you revealed."""
    stats: dict[str, dict] = {}
    for entry in load_progress().values():
        for bid, found in (entry.get("found_at_reveal") or {}).items():
            t = (entry.get("types") or {}).get(bid, "?")
            s = stats.setdefault(t, {"type": t, "found": 0, "missed": 0})
            s["found" if found else "missed"] += 1
    return sorted(stats.values(), key=lambda s: (-s["missed"], s["type"]))


# ---------------------------------------------------------------------- CLI

GREEN, RED, YELLOW, DIM, BOLD, RESET = "\033[32m", "\033[31m", "\033[33m", "\033[2m", "\033[1m", "\033[0m"


def _print_tests(r: dict, verbose: bool) -> None:
    for t in r["tests"]:
        colour = GREEN if t["total"] and t["passed"] == t["total"] else RED
        print(f"{BOLD}{t['label']}{RESET}  {colour}{t['passed']}/{t['total']}{RESET}")
        for c in [c for c in r["cases"] if c["file"] == t["file"]]:
            ok = c["outcome"] == "passed"
            print(f"  {GREEN + '✔' if ok else RED + '✘'}{RESET} {c['doc'] or c['name']}")
            if not ok:
                print(f"      {RED}{c['short'].splitlines()[0][:200] if c['short'] else ''}{RESET}")
                from judge import _print_compare
                _print_compare(c.get("compare"))
                if verbose:
                    print("\n".join("      " + l for l in c["long"].splitlines()[-30:]))
    if r["error"]:
        print(f"\n{RED}{r['error']}{RESET}")
    for f in r["tampered"]:
        print(f"{YELLOW}! {f} differs from the original. It was ignored: tests ran on the original.{RESET}")
    for v in r["verified_changed"]:
        print(f"{YELLOW}! you changed VERIFIED code: {v}. The rules say not to; it won't count as solved.{RESET}")
    colour = GREEN if r["all_pass"] else RED
    print(f"\n{BOLD}{colour}{r['passed']}/{r['total']} passing{RESET}  {DIM}({r['elapsed']}s){RESET}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("set", nargs="?")
    ap.add_argument("--test", type=int, help="run only Test N")
    ap.add_argument("--main", action="store_true", help="run main.py")
    ap.add_argument("--reset", action="store_true")
    ap.add_argument("--reveal", action="store_true")
    ap.add_argument("--hint", action="store_true")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args(argv)
    if not args.set:
        for s in all_sets():
            p = s["progress"] or {}
            mark = f"{GREEN}✔{RESET}" if p.get("solved") else f"{YELLOW}…{RESET}" if p else " "
            print(f" {mark} {s['id']}  {s['length']:<4} {s['difficulty']:<6} {s['n_bugs']} bugs  {s['title']}")
        return 0
    try:
        sid = find(args.set)
    except LookupError as exc:
        print(exc, file=sys.stderr)
        return 2
    if args.reset:
        reset(sid)
        print(f"reset {workspace(sid)}")
        return 0
    if args.main:
        out = run_main(sid)
        sys.stdout.write(out["stdout"])
        sys.stderr.write(out["stderr"])
        return out["exit_code"]
    if args.hint:
        h = hint(sid)
        print(f"{h['bug'] or ''} {h['hint']}")
        return 0
    if args.reveal:
        key = answer_key(sid)
        for b in key["bugs"]:
            mark = f"{GREEN}found{RESET}" if b["you_fixed"] else f"{RED}missed{RESET}"
            print(f"{BOLD}{b['id']} {b['title']}{RESET} [{b['type']}] {b['file']}:{b['function']}  {mark}")
            print(f"  why: {b['why']}\n  buggy: {b['buggy'].strip()}\n  fixed: {b['fixed'].strip()}\n")
        return 0
    print(f"{BOLD}{sid}{RESET}  {DIM}{workspace(sid)}{RESET}\n")
    r = run_tests(sid, args.test)
    record(r)
    _print_tests(r, args.verbose)
    return 0 if r["all_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
