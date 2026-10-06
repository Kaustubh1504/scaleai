from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")


def money(value):
    return Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)


def overage(tokens, plan):
    return max(0, tokens - plan.included_tokens)


def charge(over, plan):
    amount = Decimal(over) * plan.price_per_1k / 1000
    return round(amount, 2)


def invoice(usage, tenant):
    over = overage(usage.billable_tokens, tenant.plan)
    return {
        "plan": tenant.plan.name,
        "billable_tokens": usage.billable_tokens,
        "overage_tokens": over,
        "amount": charge(over, tenant.plan),
    }


def total(invoices):
    return money(sum((inv["amount"] for inv in invoices.values()), Decimal(0)))
