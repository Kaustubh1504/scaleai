"""Clocks. Code under test takes a clock so tests never really sleep.

    clock.time()      -> float unix seconds
    clock.sleep(s)    -> wait s seconds

FakeClock.sleep() returns instantly, moves time forward and records the wait
in ``clock.sleeps`` so tests can assert on backoff schedules.
"""

from __future__ import annotations

import threading
import time as _time


class RealClock:
    def time(self) -> float:
        return _time.time()

    def sleep(self, seconds: float) -> None:
        if seconds > 0:
            _time.sleep(seconds)


class FakeClock:
    def __init__(self, start: float = 1_700_000_000.0):
        self._now = float(start)
        self.sleeps: list[float] = []
        self._lock = threading.Lock()

    def time(self) -> float:
        with self._lock:
            return self._now

    def sleep(self, seconds: float) -> None:
        if seconds < 0:
            raise ValueError(f"cannot sleep a negative duration: {seconds!r}")
        with self._lock:
            self.sleeps.append(seconds)
            self._now += seconds

    def advance(self, seconds: float) -> None:
        with self._lock:
            self._now += seconds

    def set(self, t: float) -> None:
        with self._lock:
            self._now = float(t)

    @property
    def total_slept(self) -> float:
        return sum(self.sleeps)
