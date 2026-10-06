class SmoothWeightedRR:
    """Smooth weighted round robin (the nginx algorithm)."""

    def __init__(self, backends):
        self.backends = backends
        self.current = {bid: 0 for bid in backends}

    # VERIFIED
    def pick(self, eligible):
        if not eligible:
            return None
        total = 0
        for bid in eligible:
            self.current[bid] += self.backends[bid].weight
            total += self.backends[bid].weight
        chosen = min(eligible, key=lambda bid: (-self.current[bid], bid))
        self.current[chosen] -= total
        return chosen
