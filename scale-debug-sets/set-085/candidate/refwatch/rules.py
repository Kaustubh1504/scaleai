"""Referral rules: qualifying deposits, self-referrals, signup bursts and the bonus ledger."""
from collections import defaultdict
from decimal import Decimal

from .timeutil import minutes_between, within_days

BONUS_USD = 25
MIN_DEPOSIT = Decimal("20.00")
QUALIFY_DAYS = 14
BURST_SIZE = 3
BURST_MINUTES = 60


def referrals(accounts):
    """{referrer: [referred account ids in file order]}."""
    out = defaultdict(list)
    for acct in accounts.values():
        if acct.referred_by:
            out[acct.referred_by].append(acct.id)
    return dict(out)


def is_qualifying(deposit, account):
    return (deposit.status == "settled"
            and deposit.amount >= MIN_DEPOSIT
            and within_days(account.signup_at, deposit.at, QUALIFY_DAYS))


def qualifying_accounts(accounts, deposits):
    """Referred accounts with at least one qualifying deposit."""
    return {d.account for d in deposits
            if accounts[d.account].referred_by and is_qualifying(d, accounts[d.account])}


def self_referrals(accounts, rings_by_account):
    """Referred accounts that sit in the same ring as their referrer."""
    found = set()
    for acct in accounts.values():
        ring = rings_by_account.get(acct.id)
        if acct.referred_by and ring is not None and rings_by_account.get(acct.referred_by) == ring:
            found.add(acct.id)
    return found


def has_burst(signups):
    times = sorted(signups)
    for i in range(len(times) - BURST_SIZE + 1):
        if minutes_between(times[i], times[i + BURST_SIZE - 1]) <= BURST_MINUTES:
            return True
    return False


def bonus_ledger(accounts, deposits, self_referred):
    """One (referrer, account, deposit_id) entry per bonus, walking deposits in time order."""
    ledger = []
    paid = set()
    for dep in sorted(deposits, key=lambda d: (d.at, d.id)):
        acct = accounts[dep.account]
        if not acct.referred_by or acct.id in self_referred or acct.id in paid:
            continue
        if not is_qualifying(dep, acct):
            continue
        ledger.append((acct.referred_by, acct.id, dep.id))
    return ledger
