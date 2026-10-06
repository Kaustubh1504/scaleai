from collections import defaultdict

from .models import Statement
from .rules import counts_toward_pay, line_amount


def adjustment_totals(adjustments, totals={"bonus": 0, "clawback": 0}):
    for adj in adjustments:
        totals[adj.kind] += adj.cents
    return totals


def build_statements(contributors, entries, adjustments, rates):
    """Return ({contributor_id: Statement} for active contributors, unmatched adjustment count)."""
    work = defaultdict(list)
    for entry in entries:
        work[entry.contributor_id].append(entry)
    extras = defaultdict(list)
    unmatched = 0
    for adj in adjustments:
        if adj.contributor_id in contributors:
            extras[adj.contributor_id].append(adj)
        else:
            unmatched += 1

    statements = {}
    for cid in sorted(contributors):
        person = contributors[cid]
        if not person.active:
            continue
        st = Statement(cid, carryover=person.carryover)
        for entry in work.get(cid, []):
            if counts_toward_pay(entry, rates):
                st.lines += 1
                st.earned += line_amount(entry, rates, person.tier)
        totals = adjustment_totals(extras.get(cid, []))
        st.bonus, st.clawback = totals["bonus"], totals["clawback"]
        statements[cid] = st
    return statements, unmatched
