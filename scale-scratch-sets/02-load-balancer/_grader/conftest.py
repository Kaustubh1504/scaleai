"""Hidden acceptance tests for 02-load-balancer.

    python -m pytest _grader -q -p no:cacheprovider                               # grade your code (problem root)
    SOLUTION_DIR=_grader/reference python -m pytest _grader -q -p no:cacheprovider   # self-check the grader

Everything is imported lazily inside fixtures, so a missing lb/balancer.py gives one clear
error per test instead of a collection crash.
"""

from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
PROBLEM = HERE.parent
SOLUTION_DIR = Path(os.environ.get("SOLUTION_DIR", PROBLEM)).resolve()
sys.path.insert(0, str(SOLUTION_DIR))


def pytest_report_header(config):
    return f"solution under test: {SOLUTION_DIR}"


class Clock:
    """Fake clock: pass the instance itself as `now` (it is callable)."""

    def __init__(self, t: float = 0.0):
        self.t = float(t)

    def __call__(self) -> float:
        return self.t

    def set(self, t: float) -> None:
        self.t = float(t)

    def advance(self, dt: float) -> None:
        self.t += dt


@pytest.fixture
def m():
    """The candidate's lb.balancer module."""
    try:
        return importlib.import_module("lb.balancer")
    except ModuleNotFoundError as e:
        pytest.fail(f"could not import lb.balancer from {SOLUTION_DIR}: {e}", pytrace=False)


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def make(m, clock):
    """make(**kwargs) -> LoadBalancer wired to the fake clock."""

    def _make(**kw):
        return m.LoadBalancer(clock, **kw)

    return _make


@pytest.fixture
def lb(make):
    return make()
