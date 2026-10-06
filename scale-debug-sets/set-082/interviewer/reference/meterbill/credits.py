def apply_credits(invoices, credits):
    """Apply credits in file order. Returns the ids of credits with no matching invoice."""
    unapplied = []
    for credit in credits:
        inv = invoices.get((credit.tenant_id, credit.month))
        if inv is None:
            unapplied.append(credit.credit_id)
            continue
        room = inv.total_cents - inv.credits_cents
        inv.credits_cents += min(credit.amount_cents, room)
        inv.credit_ids.append(credit.credit_id)
    return unapplied
