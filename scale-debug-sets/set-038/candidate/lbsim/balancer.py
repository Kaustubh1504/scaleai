def release_finished(backends, now_ms):
    for b in backends.values():
        b.active = [end for end in b.active if end >= now_ms]


def candidates(backends, pool):
    return [b for b in backends.values()
            if b.pool == pool and b.enabled and b.healthy and len(b.active) < b.max_conns]


def load_of(backend):
    return len(backend.active) // backend.weight


# VERIFIED
def pick(options, sticky_id=None):
    """Sticky backend if it is still an option, else least load per weight."""
    for b in options:
        if b.id == sticky_id:
            return b
    if not options:
        return None
    return min(options, key=lambda b: (load_of(b), -b.weight, b.id))


def assign(backend, request):
    backend.active.append(request.arrival_ms + request.duration_ms)
    backend.served += 1
    backend.busy_ms += request.duration_ms
    backend.peak = max(backend.peak, len(backend.active))
