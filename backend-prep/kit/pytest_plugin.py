"""pytest plugin used by the judge.

* ``sol`` fixture: the solution module under test, loaded fresh from
  ``$SOLUTION_PATH`` for every test (so module-level state never leaks).
* ``clock`` fixture: a new FakeClock.
* Writes a JSON summary of every test (name, docstring, part, outcome,
  short and long failure text) to ``$RESULTS_PATH`` for the judge and the UI.
* For a failed comparison (``assert got == want`` or unittest's
  ``assertEqual(got, want)``) it also records both values, pretty-printed, plus
  a short list of the exact keys/indexes that differ: the "Expected vs Your
  output" panel in the UI. The left/first value is treated as your output.
"""

from __future__ import annotations

import importlib.util
import json
import os
import pprint
import re
import sys
import unittest
from pathlib import Path

import pytest

from kit.clock import FakeClock

_results: list[dict] = []
_collect_errors: list[str] = []
_docs: dict[str, str] = {}
_compare: dict[str, dict] = {}
_current: str | None = None

MAX_VALUE_CHARS = 6000
MAX_DIFFS = 12


# ------------------------------------------------------- expected vs actual


def _fmt(value) -> str:
    if isinstance(value, str) and "\n" in value:
        text = value
    else:
        try:
            text = pprint.pformat(value, width=100, compact=True, sort_dicts=True)
        except Exception:  # unsortable keys, odd reprs
            text = repr(value)
    return text if len(text) <= MAX_VALUE_CHARS else text[:MAX_VALUE_CHARS] + "\n... (truncated)"


def _short(value) -> str:
    text = repr(value)
    return text if len(text) <= 140 else text[:137] + "..."


def _diffs(got, want, path: str = "", out: list | None = None) -> list[str]:
    """Where two structures differ, e.g. "['r01']: expected [] but got ['no_answer']"."""
    out = [] if out is None else out
    if len(out) >= MAX_DIFFS:
        return out
    if isinstance(got, dict) and isinstance(want, dict):
        keys = list(want) + [k for k in got if k not in want]
        for k in keys:
            if len(out) >= MAX_DIFFS:
                break
            sub = f"{path}[{k!r}]"
            if k not in got:
                out.append(f"{sub}: missing (expected {_short(want[k])})")
            elif k not in want:
                out.append(f"{sub}: not expected (got {_short(got[k])})")
            elif got[k] != want[k]:
                _diffs(got[k], want[k], sub, out)
        return out
    if isinstance(got, (list, tuple)) and isinstance(want, (list, tuple)) and type(got) is type(want):
        if len(got) != len(want):
            out.append(f"{path or 'value'}: length {len(got)}, expected {len(want)}")
        for i, (g, w) in enumerate(zip(got, want)):
            if len(out) >= MAX_DIFFS:
                break
            if g != w:
                _diffs(g, w, f"{path}[{i}]", out)
        return out
    if got != want:
        out.append(f"{path or 'value'}: expected {_short(want)} but got {_short(got)}")
    return out


def _record(got, want, op: str = "==") -> None:
    if _current is None or _current in _compare:
        return  # keep the first failing comparison of a test
    try:
        diffs = _diffs(got, want) if op == "==" else []
    except Exception:
        diffs = []
    _compare[_current] = {"op": op, "actual": _fmt(got), "expected": _fmt(want), "diffs": diffs}


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_protocol(item, nextitem):
    global _current
    _current = item.nodeid


def pytest_assertrepr_compare(config, op, left, right):
    _record(left, right, op)
    return None  # keep pytest's own explanation in the traceback


def _wrap_unittest(name: str, op: str) -> None:
    original = getattr(unittest.TestCase, name, None)
    if original is None or getattr(original, "_kit_wrapped", False):
        return

    def wrapper(self, first, second, *args, **kwargs):
        try:
            return original(self, first, second, *args, **kwargs)
        except AssertionError:
            _record(first, second, op)
            raise

    wrapper._kit_wrapped = True
    setattr(unittest.TestCase, name, wrapper)


for _name, _op in (("assertEqual", "=="), ("assertListEqual", "=="), ("assertDictEqual", "=="),
                   ("assertTupleEqual", "=="), ("assertSetEqual", "=="), ("assertSequenceEqual", "=="),
                   ("assertCountEqual", "same items as"), ("assertAlmostEqual", "≈"),
                   ("assertNotEqual", "!="), ("assertIn", "in"), ("assertNotIn", "not in"),
                   ("assertIs", "is"), ("assertGreater", ">"), ("assertGreaterEqual", ">="),
                   ("assertLess", "<"), ("assertLessEqual", "<=")):
    _wrap_unittest(_name, _op)


def load_solution(path: str | os.PathLike[str]):
    name = "solution"
    spec = importlib.util.spec_from_file_location(name, str(path))
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def sol():
    path = os.environ.get("SOLUTION_PATH")
    if not path:
        pytest.fail("SOLUTION_PATH is not set; run tests through judge.py")
    return load_solution(path)


@pytest.fixture
def clock():
    return FakeClock()


def pytest_collection_modifyitems(items):
    for item in items:
        fn = getattr(item, "function", None)
        doc = " ".join(((fn.__doc__ or "").strip() if fn else "").split())
        callspec = getattr(item, "callspec", None)
        if doc and callspec is not None:
            doc = f"{doc} [{callspec.id}]"  # parametrized: keep each case distinguishable
        _docs[item.nodeid] = doc


def pytest_collectreport(report):
    if report.failed:
        _collect_errors.append(report.longreprtext[-6000:])


def pytest_runtest_logreport(report):
    if report.when == "call" or (report.when == "setup" and report.outcome != "passed"):
        name = report.nodeid.split("::", 1)[-1]
        m = re.match(r"test_part(\d+)_", name)
        short = ""
        long = ""
        if report.failed:
            crash = getattr(report.longrepr, "reprcrash", None)
            short = crash.message if crash is not None else str(report.longrepr).splitlines()[-1]
            long = report.longreprtext[-6000:]
        _results.append({
            "name": name,
            "file": (report.nodeid.split("::", 1)[0] or report.location[0]).rsplit("/", 1)[-1],
            "doc": _docs.get(report.nodeid, ""),
            "part": int(m.group(1)) if m else 1,
            "outcome": "error" if report.when == "setup" and report.failed else report.outcome,
            "short": short,
            "long": long,
            "stdout": (report.capstdout or "")[-3000:],
            "duration": round(report.duration, 3),
            "compare": _compare.get(report.nodeid) if report.failed else None,
        })


def pytest_sessionfinish(session):
    out = os.environ.get("RESULTS_PATH")
    if out:
        Path(out).write_text(json.dumps({"cases": _results, "collect_errors": _collect_errors}))
