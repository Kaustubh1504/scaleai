from .models import BackendState


class HealthTracker:
    """Marks a backend down after FALL consecutive failed checks and healthy again
    after RISE consecutive passes."""

    def __init__(self, backend_ids, fall, rise):
        self.fall, self.rise = fall, rise
        self.state = {bid: BackendState.HEALTHY for bid in backend_ids}
        self.fails = {bid: 0 for bid in backend_ids}
        self.passes = {bid: 0 for bid in backend_ids}
        self.transitions = []

    def observe(self, check):
        bid = check.backend
        if bid not in self.state:
            return
        if self.state[bid] is BackendState.HEALTHY:
            if check.ok:
                self.fails[bid] = 0
                return
            self.fails[bid] += 1
            if self.fails[bid] >= self.fall:
                self._move(bid, BackendState.DOWN, check.t_ms)
        else:
            self.passes[bid] = self.passes[bid] + 1 if check.ok else 0
            if self.passes[bid] >= self.rise:
                self._move(bid, BackendState.HEALTHY, check.t_ms)

    def _move(self, bid, new_state, t_ms):
        self.state[bid] = new_state
        self.fails[bid] = 0
        self.passes[bid] = 0
        self.transitions.append((t_ms, bid, new_state.value))
