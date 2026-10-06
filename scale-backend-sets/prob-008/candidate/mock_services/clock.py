"""Clocks. Use ``clock.sleep()`` / ``clock.time()`` instead of the time module so
tests can swap in ``FakeClock`` and run instantly."""

import mock_services  # noqa: F401
from shared.fake_clock import Clock, FakeClock, RealClock

__all__ = ["Clock", "FakeClock", "RealClock"]
