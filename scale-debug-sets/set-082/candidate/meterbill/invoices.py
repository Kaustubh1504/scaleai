from decimal import Decimal

from .models import Invoice
from .plans import blocks_for, tiered_cents
from .timeparse import month_of


def apply_discount(cents, pct):
    discounted = Decimal(cents) * (Decimal(100) - pct) / Decimal(100)
    return round(discounted)


def build_invoices(accepted, tenants, plans):
    invoices = {}
    for req in accepted:
        plan = plans[tenants[req.tenant_id].plan]
        if not plan.billed:
            continue
        inv = invoices.setdefault((req.tenant_id, month_of(req.ts)), Invoice(req.tenant_id, month_of(req.ts)))
        inv.usage_units += req.units
    for (tenant_id, _), inv in invoices.items():
        tenant = tenants[tenant_id]
        plan = plans[tenant.plan]
        inv.subtotal_cents = plan.monthly_fee_cents + tiered_cents(blocks_for(inv.usage_units, plan), plan.tiers)
        inv.total_cents = apply_discount(inv.subtotal_cents, tenant.discount_pct)
    return invoices
