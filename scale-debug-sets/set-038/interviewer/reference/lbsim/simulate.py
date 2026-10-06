from .balancer import assign, candidates, pick, release_finished
from .health import ProbeFeed


def run(backends, requests, probes):
    """Route requests in arrival order. Returns {request_id: backend_id or None}."""
    feed = ProbeFeed(probes)
    sticky = {}
    routes = {}
    for req in requests:
        release_finished(backends, req.arrival_ms)
        feed.advance(backends, req.arrival_ms)
        key = (req.client_id, req.pool)
        chosen = pick(candidates(backends, req.pool), sticky.get(key))
        if chosen is None:
            routes[req.request_id] = None
            continue
        assign(chosen, req)
        sticky[key] = chosen.id
        routes[req.request_id] = chosen.id
    return routes
