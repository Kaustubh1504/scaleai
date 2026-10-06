"""Pytest plugin that makes any non-loopback network connection fail.

Loaded by verify_problem.py with ``-p no_network`` to prove a problem runs offline.
"""

from __future__ import annotations

import ipaddress
import socket

_real_connect = socket.socket.connect
_real_connect_ex = socket.socket.connect_ex


def _is_loopback(address) -> bool:
    if not isinstance(address, tuple):
        return True  # AF_UNIX paths
    host = address[0]
    if host in ("localhost", ""):
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def _guarded(real):
    def connect(self, address):
        if not _is_loopback(address):
            raise OSError(f"network access blocked during verification: {address!r}")
        return real(self, address)

    return connect


def pytest_configure(config):
    socket.socket.connect = _guarded(_real_connect)
    socket.socket.connect_ex = _guarded(_real_connect_ex)


def pytest_unconfigure(config):
    socket.socket.connect = _real_connect
    socket.socket.connect_ex = _real_connect_ex
