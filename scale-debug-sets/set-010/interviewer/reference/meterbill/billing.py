import math


def invoice(tenant, tokens):
    plan = tenant.plan
    excess = max(0, tokens - plan.included_tokens)
    blocks = math.ceil(excess / 1000)
    overage = round(blocks * plan.overage_per_1k, 2)
    subtotal = plan.base_fee + overage
    discount = round(subtotal * tenant.discount_pct / 100, 2)
    return {
        "plan": plan.name,
        "base": plan.base_fee,
        "overage": overage,
        "discount": discount,
        "total": round(subtotal - discount, 2),
    }
