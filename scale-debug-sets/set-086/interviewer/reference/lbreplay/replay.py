from .balancer import SmoothWeightedRR
from .health import HealthTracker
from .models import BackendState
from .sessions import StickyTable, has_room


class Replay:
    def __init__(self, backends, config):
        self.backends = backends
        self.health = HealthTracker(sorted(backends), config["fall"], config["rise"])
        self.rr = SmoothWeightedRR(backends)
        self.sticky = StickyTable()
        self.inflight = {bid: [] for bid in backends}  # end times of running requests
        self.assignments = {}
        self.failovers = 0

    def active(self, bid, now):
        self.inflight[bid] = [end for end in self.inflight[bid] if end > now]
        return len(self.inflight[bid])

    def usable(self, bid, now):
        return self.health.state[bid] is BackendState.HEALTHY and self.active(bid, now) < self.backends[bid].max_conns

    def route(self, request):
        now = request.t_ms
        previous = self.sticky.lookup(request.session)
        chosen = None
        if previous is not None and self.health.state[previous] is BackendState.HEALTHY:
            if has_room(self.backends[previous], self.active(previous, now)):
                chosen = previous
        if chosen is None:
            eligible = [bid for bid in sorted(self.backends) if self.usable(bid, now)]
            chosen = self.rr.pick(eligible)
            if previous is not None and chosen is not None and chosen != previous:
                self.failovers += 1
        if chosen is not None:
            self.inflight[chosen].append(now + request.duration_ms)
            self.sticky.remember(request.session, chosen)
        self.assignments[request.id] = chosen
        return chosen

    def run(self, requests, checks):
        pending = list(checks)
        for request in requests:
            while pending and pending[0].t_ms <= request.t_ms:
                self.health.observe(pending.pop(0))
            self.route(request)
        for check in pending:
            self.health.observe(check)
        return self
