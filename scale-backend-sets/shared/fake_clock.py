"""Clocks that share one interface so time-based code is testable.

Code under test should take a ``clock`` argument and only ever call
``clock.time()``, ``clock.monotonic()``, ``clock.sleep()`` or
``await clock.asleep()``. Production wires in ``RealClock()``; tests wire in
``FakeClock()`` and move time explicitly, so retries, TTLs, leases and
heartbeats can be tested instantly and deterministically.
"""

from __future__ import annotations

import asyncio
import heapq
import itertools
import threading
import time as _time
from typing import Callable, Protocol


class Clock(Protocol):
    def time(self) -> float: ...

    def monotonic(self) -> float: ...

    def sleep(self, seconds: float) -> None: ...

    async def asleep(self, seconds: float) -> None: ...


class RealClock:
    """Wall-clock time. Use in production code paths."""

    def time(self) -> float:
        return _time.time()

    def monotonic(self) -> float:
        return _time.monotonic()

    def sleep(self, seconds: float) -> None:
        if seconds > 0:
            _time.sleep(seconds)

    async def asleep(self, seconds: float) -> None:
        await asyncio.sleep(max(0.0, seconds))


def elapse(clock: Clock, seconds: float) -> None:
    """Let time pass inside a mock service.

    On a ``FakeClock`` this advances time without recording it in ``sleeps``,
    so ``sleeps`` only ever shows the sleeps made by the code under test.
    """
    if seconds <= 0:
        return
    if isinstance(clock, FakeClock):
        clock.advance(seconds)
    else:
        clock.sleep(seconds)


async def aelapse(clock: Clock, seconds: float) -> None:
    if isinstance(clock, FakeClock):
        clock.advance(max(0.0, seconds))
        await asyncio.sleep(0)
    else:
        await clock.asleep(seconds)


class TimerHandle:
    def __init__(self, due: float, callback: Callable[[], None]):
        self.due = due
        self.callback = callback
        self.cancelled = False

    def cancel(self) -> None:
        self.cancelled = True


class FakeClock:
    """A manually driven clock.

    * ``sleep(s)`` returns immediately, advances time by ``s`` and records
      ``s`` in ``self.sleeps`` (so tests can assert on backoff schedules).
    * ``advance(s)`` moves time forward, firing any ``call_later`` timers that
      become due, in due-time order, with the clock set to each timer's due
      time while its callback runs.
    * ``time()`` and ``monotonic()`` return the same value.

    Thread-safe. Concurrent sleeps from several threads each advance the
    shared clock; tests that need precise timing should sleep from one thread.
    """

    def __init__(self, start: float = 1_700_000_000.0):
        self._now = float(start)
        self._lock = threading.RLock()
        self._timers: list[tuple[float, int, TimerHandle]] = []
        self._seq = itertools.count()
        self.sleeps: list[float] = []

    def time(self) -> float:
        with self._lock:
            return self._now

    def monotonic(self) -> float:
        return self.time()

    def advance(self, seconds: float) -> None:
        if seconds < 0:
            raise ValueError("cannot move a clock backwards")
        with self._lock:
            target = self._now + seconds
        while True:
            with self._lock:
                if not self._timers or self._timers[0][0] > target:
                    self._now = max(self._now, target)
                    return
                due, _, handle = heapq.heappop(self._timers)
                self._now = max(self._now, due)
            if not handle.cancelled:
                handle.callback()

    def set(self, timestamp: float) -> None:
        """Jump to an absolute time (must not be in the past)."""
        self.advance(timestamp - self.time())

    def sleep(self, seconds: float) -> None:
        with self._lock:
            self.sleeps.append(seconds)
        self.advance(max(0.0, seconds))

    async def asleep(self, seconds: float) -> None:
        self.sleep(seconds)
        # Yield so other tasks get a turn, like a real sleep would.
        await asyncio.sleep(0)

    def call_later(self, delay: float, callback: Callable[[], None]) -> TimerHandle:
        """Run ``callback`` when the clock is advanced past now + delay."""
        with self._lock:
            handle = TimerHandle(self._now + delay, callback)
            heapq.heappush(self._timers, (handle.due, next(self._seq), handle))
            return handle
