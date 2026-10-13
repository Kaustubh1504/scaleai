"""Hidden acceptance tests for 05-task-processor.

    python -m pytest _grader -q                                  # grade your code (problem root)
    SOLUTION_DIR=_grader/reference python -m pytest _grader -q   # self-check the grader

Your solution is `processor.py` (with `class TaskProcessor`) in SOLUTION_DIR,
which defaults to the problem root.
"""

from __future__ import annotations

import contextlib
import importlib
import os
import signal
import sys
import time
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
PROBLEM = HERE.parent
SOLUTION_DIR = Path(os.environ.get("SOLUTION_DIR", PROBLEM)).resolve()
sys.path.insert(0, str(SOLUTION_DIR))

PERF_LIMIT = 2.0  # seconds per performance test (the reference takes well under 1 s)


def pytest_report_header(config):
    return f"solution under test: {SOLUTION_DIR}"


@pytest.fixture
def TP():
    """The TaskProcessor class, imported lazily so a missing file gives one clear error per test."""
    if not (SOLUTION_DIR / "processor.py").exists():
        pytest.fail(f"processor.py not found in {SOLUTION_DIR}", pytrace=False)
    try:
        mod = importlib.import_module("processor")
    except Exception as e:  # syntax errors, bad imports, ...
        pytest.fail(f"importing processor.py failed: {type(e).__name__}: {e}", pytrace=False)
    if not hasattr(mod, "TaskProcessor"):
        pytest.fail("processor.py has no class TaskProcessor", pytrace=False)
    return mod.TaskProcessor


@pytest.fixture
def tp(TP):
    return TP()


def drain(p, limit=10**7):
    """Consume until None; returns the ids in order."""
    out = []
    for _ in range(limit):
        t = p.consume_task()
        if t is None:
            return out
        out.append(t)
    raise AssertionError("consume_task never returned None")


@contextlib.contextmanager
def time_limit(seconds=PERF_LIMIT, what="operation"):
    """Hard wall-clock limit (SIGALRM), so an O(n)-per-op solution fails instead of hanging."""

    def _boom(signum, frame):
        raise TimeoutError(f"{what} took longer than {seconds:.1f}s (O(n) per operation?)")

    old = signal.signal(signal.SIGALRM, _boom)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    start = time.perf_counter()
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old)
    elapsed = time.perf_counter() - start
    assert elapsed < seconds, f"{what} took {elapsed:.2f}s (limit {seconds:.1f}s)"
