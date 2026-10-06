BLOCK_UNITS = 1000


def parse_rate(text):
    """`N/Ws` or `N/Wm` -> (N, window in seconds)."""
    count, window = text.replace(" ", "").split("/")
    if window.endswith("m"):
        return int(count), int(window[:-1]) * 60
    return int(count), int(window.rstrip("s"))


def effective_limit(tenant, plan):
    if tenant.rate_override:
        return parse_rate(tenant.rate_override)
    return plan.limit, plan.window_s


def blocks_for(units, plan):
    billable = max(0, units - plan.included_units)
    return billable // BLOCK_UNITS  # whole blocks


# VERIFIED
def tiered_cents(blocks, tiers):
    cents, floor = 0, 0
    for tier in tiers:
        ceiling = blocks if tier.up_to_blocks is None else min(blocks, tier.up_to_blocks)
        if ceiling > floor:
            cents += (ceiling - floor) * tier.cents_per_block
        if tier.up_to_blocks is None or blocks <= tier.up_to_blocks:
            break
        floor = tier.up_to_blocks
    return cents
