"""Runs the candidate's test_*(impl) functions against the correct client and each mutant."""

import importlib.util
import inspect
import traceback
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def candidate_tests(sol):
    tests = [obj for name, obj in vars(sol).items()
             if name.startswith("test_") and inspect.isfunction(obj) and obj.__module__ == sol.__name__]
    return sorted(tests, key=lambda f: f.__code__.co_firstlineno)


def run(test, impl):
    """None if the test passed, else a short description of the failure."""
    try:
        test(impl)
    except (Exception, pytest.fail.Exception) as exc:
        last = traceback.extract_tb(exc.__traceback__)[-1]
        return f"{type(exc).__name__}: {exc}".strip().splitlines()[0][:200] + f" (line {last.lineno})"
    return None


def passing_tests(sol):
    correct = load(HERE / "client_impl.py", "client_impl_correct")
    return [t for t in candidate_tests(sol) if run(t, correct) is None]


def check_mutant(sol, n):
    tests = passing_tests(sol)
    assert tests, "none of your tests pass against the correct client, so nothing can catch a mutant"
    mutant = load(HERE / "mutants" / f"m{n}.py", f"client_mutant_{n}")
    caught = [t.__name__ for t in tests if run(t, mutant) is not None]
    assert caught, f"all {len(tests)} of your passing tests also pass against mutant m{n}: {mutant.__doc__.strip()}"


def test_correct_client_passes(sol):
    """All your tests pass against the correct client"""
    tests = candidate_tests(sol)
    assert tests, "define at least one function named test_*(impl)"
    correct = load(HERE / "client_impl.py", "client_impl_correct")
    failures = {t.__name__: err for t in tests if (err := run(t, correct)) is not None}
    assert not failures, f"these tests fail against the CORRECT client (so they're wrong): {failures}"


def test_catches_m1(sol):
    """Catches mutant: stops one page early"""
    check_mutant(sol, 1)


def test_catches_m2(sol):
    """Catches mutant: retries client errors such as 404"""
    check_mutant(sol, 2)


def test_catches_m3(sol):
    """Catches mutant: ignores Retry-After"""
    check_mutant(sol, 3)


def test_catches_m4(sol):
    """Catches mutant: sleeps after the final attempt"""
    check_mutant(sol, 4)


def test_catches_m5(sol):
    """Catches mutant: drops the last item"""
    check_mutant(sol, 5)


def test_catches_m6(sol):
    """Catches mutant: gives up one attempt early"""
    check_mutant(sol, 6)


def test_catches_m7(sol):
    """Catches mutant: returns partial results instead of raising"""
    check_mutant(sol, 7)


def test_catches_m8(sol):
    """Catches mutant: backoff does not grow"""
    check_mutant(sol, 8)
