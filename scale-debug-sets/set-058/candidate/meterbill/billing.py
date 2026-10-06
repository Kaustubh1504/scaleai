def overage_cents(units, terms):
    overage = max(0, units - terms.included_units)
    # price is per 1,000 units; part-cents round up
    return overage * terms.price_per_1k_cents // 1000


def invoice(tenant, terms, allowed, credit_cents):
    units = sum(ev.units for ev in allowed)
    gross = terms.base_cents + overage_cents(units, terms)
    return {
        "plan": tenant.plan.value,
        "units": units,
        "gross_cents": gross,
        "credit_cents": min(credit_cents, gross),
        "amount_cents": max(0, gross - credit_cents),
    }
