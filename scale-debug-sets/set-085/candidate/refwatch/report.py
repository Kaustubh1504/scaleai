"""Assemble the payout review report."""
from collections import Counter

from .links import build_rings, ring_index
from .loader import DATA_DIR, load_accounts, load_deposits, load_logins
from .rules import (BONUS_USD, bonus_ledger, has_burst, qualifying_accounts, referrals,
                    self_referrals)


def build_report(data_dir=DATA_DIR):
    accounts = load_accounts(data_dir)
    deposits = load_deposits(accounts, data_dir)
    logins, shared = load_logins(accounts, data_dir)

    rings = build_rings(accounts, logins, shared)
    self_referred = self_referrals(accounts, ring_index(rings))
    qualifying = qualifying_accounts(accounts, deposits)
    earned = Counter(referrer for referrer, _, _ in bonus_ledger(accounts, deposits, self_referred))

    rows = {}
    for referrer, referred in sorted(referrals(accounts).items()):
        flags = []
        if any(a in self_referred for a in referred):
            flags.append("self_referral")
        if has_burst([accounts[a].signup_at for a in referred]):
            flags.append("burst")
        rows[referrer] = {
            "referred": len(referred),
            "qualifying": sum(a in qualifying for a in referred),
            "self_referrals": sum(a in self_referred for a in referred),
            "payout_usd": BONUS_USD * earned[referrer],
            "flags": flags,
            "held": bool(flags),
        }

    released = {r: row for r, row in rows.items() if not row["held"]}
    summary = {
        "held": sorted(r for r, row in rows.items() if row["held"]),
        "releasable_usd": sum(row["payout_usd"] for row in released.values()),
        "top_referrer": min(released, key=lambda r: (-released[r]["payout_usd"], r)) if released else None,
    }
    return {"rings": rings, "referrers": rows, "summary": summary}
