# 21. Fake clock for tests (no real sleeping)
# Standalone: copy this file as-is. Deps: stdlib

from types import SimpleNamespace


def fake_clock(start: float = 1_700_000_000.0):
    """clock.time(), clock.monotonic(), clock.sleep(s) (returns instantly), clock.advance(s), clock.sleeps.
    Inject it wherever code would call time.time() / time.monotonic() / time.sleep()."""
    state = {"now": float(start)}
    sleeps = []

    def advance(seconds: float) -> None:
        state["now"] += seconds

    def sleep(seconds: float) -> None:
        sleeps.append(seconds)
        advance(seconds)

    return SimpleNamespace(time=lambda: state["now"], monotonic=lambda: state["now"],
                           sleep=sleep, advance=advance, sleeps=sleeps)
