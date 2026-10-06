FAILS_TO_DOWN = 2


def apply_probe(backend, probe):
    """Down after FAILS_TO_DOWN consecutive failed probes; one good probe brings it back."""
    if probe.healthy:
        backend.fails = 0
        backend.healthy = True
    else:
        backend.fails += 1
        if backend.fails >= FAILS_TO_DOWN:
            backend.healthy = False


class ProbeFeed:
    def __init__(self, probes):
        self._probes = list(probes)
        self._next = 0

    def advance(self, backends, now_ms):
        """Apply every probe taken at or before now_ms."""
        while self._next < len(self._probes) and self._probes[self._next].at_ms <= now_ms:
            probe = self._probes[self._next]
            if probe.backend_id in backends:
                apply_probe(backends[probe.backend_id], probe)
            self._next += 1
