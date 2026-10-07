"""Group accounts into rings: accounts joined by a shared device or a private IP."""
from collections import defaultdict


# VERIFIED
def find(parent, x):
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x


def union(parent, a, b):
    ra, rb = find(parent, a), find(parent, b)
    if ra != rb:
        parent[max(ra, rb)] = min(ra, rb)


def build_rings(accounts, logins, shared_networks):
    """Return rings (sorted id lists of 2+ accounts), biggest first, then by first id."""
    parent = {acct_id: acct_id for acct_id in accounts}
    members = defaultdict(list)
    for acct in accounts.values():
        if acct.device:
            members[("device", acct.device)].append(acct.id)
    for acct_id, ip in logins:
        if ip not in shared_networks:
            members[("ip", ip)].append(acct_id)
    for ids in members.values():
        for other in ids[1:]:
            union(parent, ids[0], other)
    groups = defaultdict(list)
    for acct_id in accounts:
        groups[find(parent, acct_id)].append(acct_id)
    rings = [sorted(g) for g in groups.values() if len(g) > 1]
    return sorted(rings, key=lambda ring: (-len(ring), ring[0]))


def ring_index(rings):
    """{account_id: ring number} for every account that is in a ring."""
    return {acct_id: n for n, ring in enumerate(rings) for acct_id in ring}
